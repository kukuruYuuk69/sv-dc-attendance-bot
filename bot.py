import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, time, timedelta
import pytz
import os

# Auto-load .env jika file ada
if os.path.exists(".env"):
    with open(".env", "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)
WIB = pytz.timezone("Asia/Jakarta")

# Database SQLite Lokal
conn = sqlite3.connect("attendance.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        user_id TEXT,
        date TEXT,
        PRIMARY KEY (user_id, date)
    )
''')
# Tabel riwayat rekap mingguan dan pelanggaran beruntun
cursor.execute('''
    CREATE TABLE IF NOT EXISTS weekly_recap (
        user_id TEXT,
        week_key TEXT,
        attendance_count INTEGER,
        is_violation INTEGER,
        consecutive_violations INTEGER,
        PRIMARY KEY (user_id, week_key)
    )
''')
conn.commit()

# Role & Channel IDs
def get_config():
    return {
        "absen_channel_id": int(os.getenv("ABSEN_CHANNEL_ID", "1570440259316088953")),
        "rekap_channel_id": int(os.getenv("REKAP_CHANNEL_ID", "1570460912572178443")),
        "role_wajib_absen_id": int(os.getenv("ROLE_WAJIB_ABSEN_ID", "1500083857591107744")),
        "log_channel_id": int(os.getenv("LOG_CHANNEL_ID", "0")),
        "role_moderator_ids": [
            int(r.strip()) for r in os.getenv("ROLE_MODERATOR_IDS", "1500812071024197682,1500811613794599022").split(",") if r.strip()
        ]
    }

def is_staff(member):
    if not member:
        return False
    cfg = get_config()
    is_admin = member.guild_permissions.administrator
    is_mod = any(role.id in cfg["role_moderator_ids"] for role in member.roles)
    return is_admin or is_mod

# Helper Pengiriman Log Audit
async def send_audit_log(guild, title, description, color=discord.Color.blue(), fields=None):
    cfg = get_config()
    log_channel_id = cfg["log_channel_id"]
    if not log_channel_id:
        return
    channel = guild.get_channel(log_channel_id)
    if not channel:
        return

    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(pytz.UTC)
    )
    if fields:
        for name, val in fields.items():
            embed.add_field(name=name, value=val, inline=False)
    embed.set_footer(text="Sistem Audit Absensi PASPAMPRES")
    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Gagal mengirim audit log: {e}")

# Helper Siklus Minggu (Senin s/d Minggu)
def get_current_week_bounds(ref_date=None):
    if ref_date is None:
        ref_date = datetime.now(WIB)
    start_monday = ref_date - timedelta(days=ref_date.weekday())
    end_sunday = start_monday + timedelta(days=6)
    week_key = start_monday.strftime("%Y-W%W")
    return start_monday.strftime("%Y-%m-%d"), end_sunday.strftime("%Y-%m-%d"), week_key

# Template Teks Pembukaan (07:00 WIB)
TEMPLATE_ABSEN_HINT = """📋 **TEMPLATE ABSENSI:**
```text
Nama: 
Pangkat: 
Job: 
Divisi: 
Status: Hadir
Ping: <@&1500812071024197682>
```
*(Wajib menyertakan screenshot/foto in-game)*"""

OPENING_MESSAGE = f"""⏰ 【 SINYAL DINAS ON DUTY DIMULAI 】⏰

Perhatian seluruh anggota PASPAMPRES,
waktu dinas telah dimulai. Segera siapkan diri dan fokus pada pelaksanaan tugas.
```- Wajib menjaga disiplin tanpa pengecualian
- Patuh mutlak terhadap perintah atasan
- Jaga kehormatan dan nama baik paspampres
- Tidak mentolerir pelanggaran dalam bentuk apapun
- Laksanakan tugas dengan sigap, tepat, dan bertanggung jawab```
⚠️ Setiap pelanggaran akan ditindak sesuai aturan yang berlaku.

━━━━━━━━━━━━━━━━━━
📢 PELAPORAN:
Apabila terdapat personel masalah atau tidak sesuai aturan.
segera laporkan ke <@&1500812071024197682> <@&1500811613794599022> 
━━━━━━━━━━━━━━━━━━
_"DISIPLIN ADALAH KEHORMATAN.
LOYALITAS ADALAH TANGGUNG JAWAB.
PROFESIONALISME ADALAH JATI DIRI."_

Setia, waspada, jujur dan tanggung jawab.

<@&1500083857591107744>

━━━━━━━━━━━━━━━━━━
{TEMPLATE_ABSEN_HINT}"""

# Template Teks Penutupan (22:00 WIB)
CLOSING_MESSAGE = """# 【 WAKTU ISTIRAHAT TELAH TIBA 】

Seluruh personel Paspampres ANS dipersilakan mengakhiri aktivitas dan memasuki waktu istirahat.

```- Gunakan waktu malam untuk memulihkan energi
- Hindari aktivitas yang mengganggu kesiapan esok hari
- Jaga sikap dan ketertiban di lingkungan masing-masing
- Pastikan kesiapan untuk pelaksanaan dinas berikutnya```
━━━━━━━━━━━━━━━━━━
💤 Istirahat yang cukup adalah bagian dari kesiapan tempur.
━━━━━━━━━━━━━━━━━━
<@&1500083857591107744>"""

last_pinned_opening_id = None

async def send_opening_announcement(channel):
    global last_pinned_opening_id
    try:
        if last_pinned_opening_id:
            try:
                old_msg = await channel.fetch_message(last_pinned_opening_id)
                if old_msg.pinned:
                    await old_msg.unpin()
            except Exception as e:
                print(f"Gagal unpin pesan lama ({last_pinned_opening_id}): {e}")

        new_msg = await channel.send(OPENING_MESSAGE)
        await new_msg.pin()
        last_pinned_opening_id = new_msg.id
        print("Pengumuman pembukaan dinas terkirim dan berhasil di-pin.")
    except Exception as e:
        print(f"Error pada pengumuman pembukaan: {e}")

async def send_closing_announcement(channel):
    try:
        await channel.send(CLOSING_MESSAGE)
        print("Pengumuman penutupan dinas terkirim.")
    except Exception as e:
        print(f"Error pada pengumuman penutupan: {e}")

# Fungsi Rekap Mingguan Inti
async def run_weekly_recap(guild, target_channel=None, is_manual=False):
    cfg = get_config()
    channel = target_channel or guild.get_channel(cfg["rekap_channel_id"])
    if not channel:
        print(f"Channel rekap ({cfg['rekap_channel_id']}) tidak ditemukan!")
        return

    wajib_role = guild.get_role(cfg["role_wajib_absen_id"])
    if not wajib_role:
        print(f"Role wajib absen ({cfg['role_wajib_absen_id']}) tidak ditemukan!")
        return

    # Ambil batas tanggal minggu berjalan (Senin s/d Minggu)
    monday_str, sunday_str, current_week_key = get_current_week_bounds()

    # Hitung week key minggu lalu untuk tracking pelanggaran beruntun
    prev_ref = datetime.now(WIB) - timedelta(days=7)
    _, _, prev_week_key = get_current_week_bounds(prev_ref)

    # Query seluruh data absensi dalam rentang minggu ini (menggunakan query batch yang akurat)
    cursor.execute(
        "SELECT user_id, COUNT(DISTINCT date) as cnt FROM attendance WHERE date >= ? AND date <= ? GROUP BY user_id",
        (monday_str, sunday_str)
    )
    attendance_map = dict(cursor.fetchall())

    normal_members = []
    violating_members = []
    consecutive_violators = []

    # Filter seluruh member yang memiliki role wajib absen (kecuali bot)
    target_members = [m for m in wajib_role.members if not m.bot]

    for m in target_members:
        user_id_str = str(m.id)
        count = attendance_map.get(user_id_str, 0)
        is_violation = 1 if count < 3 else 0

        # Cek status pelanggaran minggu lalu dari tabel weekly_recap
        cursor.execute(
            "SELECT consecutive_violations FROM weekly_recap WHERE user_id = ? AND week_key = ?",
            (user_id_str, prev_week_key)
        )
        prev_row = cursor.fetchone()
        prev_consec = prev_row[0] if prev_row else 0

        consecutive = (prev_consec + 1) if is_violation else 0

        # Catat snapshot rekap minggu ini
        cursor.execute(
            '''INSERT OR REPLACE INTO weekly_recap 
               (user_id, week_key, attendance_count, is_violation, consecutive_violations)
               VALUES (?, ?, ?, ?, ?)''',
            (user_id_str, current_week_key, count, is_violation, consecutive)
        )

        if is_violation:
            if consecutive >= 2:
                consecutive_violators.append((m, count, consecutive))
            else:
                violating_members.append((m, count))
        else:
            normal_members.append((m, count))

    conn.commit()

    # Urutkan berdasarkan kehadiran terbanyak
    normal_members.sort(key=lambda x: x[1], reverse=True)
    violating_members.sort(key=lambda x: x[1])

    # Header Embed
    embed = discord.Embed(
        title="📊 REKAPITULASI DINAS MINGGUAN PASPAMPRES",
        description=(
            f"**Periode Dinas:** `{monday_str}` s/d `{sunday_str}`\n"
            f"**Total Personel Wajib Absen:** {len(target_members)} Personel\n"
            f"**Standar Kedisiplinan:** Minimal 3x Hadir / Minggu\n"
            f"**Status Rekapitulasi:** {'On-Demand (Manual Staff)' if is_manual else 'Otomatis Penutupan Minggu'}"
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now(pytz.UTC)
    )

    # Helper untuk chunking teks agar tidak melebihi limit 1024 karakter per field Discord Embed
    def add_chunked_field(target_embed, field_title, lines, empty_text="Tidak ada personel."):
        if not lines:
            target_embed.add_field(name=field_title, value=empty_text, inline=False)
            return

        current_chunk = []
        current_len = 0
        part = 1
        for line in lines:
            if current_len + len(line) + 1 > 1000:
                name = f"{field_title} (Bagian {part})" if part > 1 or len(lines) > len(current_chunk) else field_title
                target_embed.add_field(name=name, value="\n".join(current_chunk), inline=False)
                current_chunk = [line]
                current_len = len(line)
                part += 1
            else:
                current_chunk.append(line)
                current_len += len(line) + 1

        if current_chunk:
            name = f"{field_title} (Bagian {part})" if part > 1 else field_title
            target_embed.add_field(name=name, value="\n".join(current_chunk), inline=False)

    # 1. Field Personel Memenuhi Standar (>= 3x Hadir)
    disciplined_lines = [
        f"✅ **{m.mention}** (`{m.display_name}`): **{c}x** Hadir"
        for m, c in normal_members
    ]
    add_chunked_field(
        embed,
        f"🟢 Personel Memenuhi Standar (>= 3x) — [{len(normal_members)} Personel]",
        disciplined_lines,
        empty_text="Belum ada personel yang mencapai 3x kehadiran."
    )

    # 2. Field Personel Kurang dari 3x Hadir (Teguran / Perlu Tindak Lanjut)
    violating_lines = [
        f"⚠️ **{m.mention}** (`{m.display_name}`): **{c}x** Hadir (Kurang dari 3x)"
        for m, c in violating_members
    ]
    add_chunked_field(
        embed,
        f"🟡 Personel Kurang dari 3x Hadir (Teguran) — [{len(violating_members)} Personel]",
        violating_lines,
        empty_text="Seluruh personel memenuhi standar minimal!"
    )

    # 3. Field Pelanggaran 2+ Minggu Berturut-turut (Jika Ada)
    if consecutive_violators:
        consec_lines = [
            f"🚨 **{m.mention}** (`{m.display_name}`): **{c}x** Hadir (Melanggar **{consec} minggu berturut-turut**)"
            for m, c, consec in consecutive_violators
        ]
        add_chunked_field(
            embed,
            f"🔴 PERINGATAN DARURAT: Pelanggaran 2+ Minggu — [{len(consecutive_violators)} Personel]",
            consec_lines
        )

    embed.set_footer(text="Sistem Otomasi Kedisiplinan PASPAMPRES • Format Embed Aman")
    await channel.send(embed=embed)

    # Notifikasi Peringatan & Tag Jajaran Pengawas
    mod_tag_str = " ".join([f"<@&{r}>" for r in cfg["role_moderator_ids"]])
    if consecutive_violators:
        consec_mentions = " ".join([m.mention for m, _, _ in consecutive_violators])
        await channel.send(
            f"🚨 **PERINGATAN TINGKAT TINGGI KEDISIPLINAN!** 🚨\n"
            f"Personel berikut melanggar standar kehadiran **2 MINGGU BERTURUT-TURUT**: {consec_mentions}\n"
            f"Mohon jajaran Admin & Pengawas {mod_tag_str} segera mengambil tindakan penalti kedisiplinan tegas!"
        )
    elif violating_members:
        viol_mentions = " ".join([m.mention for m, _ in violating_members])
        await channel.send(
            f"⚠️ **PERHATIAN DISIPLIN DINAS:**\n"
            f"Personel berikut belum memenuhi standar minimal 3x absen minggu ini: {viol_mentions}\n"
            f"Pemberitahuan kepada Admin & Moderator {mod_tag_str} untuk penindaklanjutan."
        )

# Jadwal Pembukaan Dinas (07:00 WIB / 00:00 UTC)
@tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.UTC))
async def schedule_opening():
    cfg = get_config()
    channel = bot.get_channel(cfg["absen_channel_id"])
    if channel:
        await send_opening_announcement(channel)

# Jadwal Penutupan Dinas Harian (22:00 WIB / 15:00 UTC)
@tasks.loop(time=time(hour=15, minute=0, tzinfo=pytz.UTC))
async def schedule_closing():
    cfg = get_config()
    channel = bot.get_channel(cfg["absen_channel_id"])
    if channel:
        await send_closing_announcement(channel)

    # Cek apakah hari ini adalah hari Minggu (WIB)
    now_wib = datetime.now(WIB)
    # now_wib.weekday() == 6 adalah hari Minggu
    if now_wib.weekday() == 6:
        print("Mengeksekusi rekapitulasi mingguan otomatis Minggu malam...")
        # Jalankan rekap di setiap guild bot terhubung
        for guild in bot.guilds:
            try:
                await run_weekly_recap(guild, is_manual=False)
            except Exception as e:
                print(f"Error eksekusi rekap mingguan di guild {guild.id}: {e}")

@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap mengamankan absensi & monitoring mingguan sesuai PRD!")
    if not schedule_opening.is_running():
        schedule_opening.start()
    if not schedule_closing.is_running():
        schedule_closing.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    cfg = get_config()
    ABSEN_CHANNEL_ID = cfg["absen_channel_id"]
    ROLE_WAJIB_ABSEN_ID = cfg["role_wajib_absen_id"]

    if message.channel.id == ABSEN_CHANNEL_ID:
        now_wib = datetime.now(WIB)
        today_str = now_wib.strftime("%Y-%m-%d")
        is_wajib = any(role.id == ROLE_WAJIB_ABSEN_ID for role in message.author.roles)

        if is_wajib:
            content = message.content

            # [FASE UJI COBA] Pengecekan absen ganda dinonaktifkan sementara
            # cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (str(message.author.id), today_str))
            # if cursor.fetchone():
            #     await message.delete()
            #     await message.channel.send(
            #         f"⚠️ {message.author.mention} Kamu sudah berhasil absen hari ini ({today_str}). Tidak diperbolehkan mengirim absen ganda!",
            #         delete_after=15
            #     )
            #     return

            # Validasi 1: Wajib Melampirkan Foto / Screenshot
            if not message.attachments:
                await message.delete()
                await message.channel.send(
                    f"❌ {message.author.mention} Absen ditolak! Wajib menyertakan screenshot/foto in-game sesuai PRD.",
                    delete_after=15
                )
                await send_audit_log(
                    message.guild,
                    "❌ Absen Ditolak (Tanpa Foto)",
                    f"Absen dari {message.author.mention} otomatis ditolak karena tidak melampirkan foto/screenshot.",
                    color=discord.Color.red()
                )
                return

            # Validasi 2: Template Teks Absensi Wajib
            required_fields = ["Nama:", "Pangkat:", "Job:", "Divisi:", "Status: Hadir", "<@&1500812071024197682>"]
            missing_fields = [f for f in required_fields if f not in content]
            if missing_fields:
                await message.delete()
                template_hint = (
                    "```text\n"
                    "Nama: \n"
                    "Pangkat: \n"
                    "Job: \n"
                    "Divisi: \n"
                    "Status: Hadir\n"
                    "Ping: <@&1500812071024197682>\n"
                    "```"
                )
                await message.channel.send(
                    f"⚠️ {message.author.mention} Format absen tidak sesuai!\n"
                    f"Wajib menggunakan template berikut secara presisi:\n{template_hint}",
                    delete_after=20
                )
                await send_audit_log(
                    message.guild,
                    "⚠️ Absen Ditolak (Format Salah)",
                    f"Absen dari {message.author.mention} ditolak karena tidak sesuai template teks wajib.",
                    color=discord.Color.orange()
                )
                return

            # Absen Diterima & Tercatat
            cursor.execute("INSERT OR REPLACE INTO attendance (user_id, date) VALUES (?, ?)", (str(message.author.id), today_str))
            conn.commit()
            await message.add_reaction("✅")

            # Kirim Audit Log Sukses
            await send_audit_log(
                message.guild,
                "✅ Absen Masuk Disetujui",
                f"Absen dari {message.author.mention} telah diverifikasi dan dicatat ke database.",
                color=discord.Color.green(),
                fields={
                    "Member": f"{message.author.name} ({message.author.id})",
                    "Tanggal": today_str,
                    "Lampiran": f"{len(message.attachments)} file gambar terlampir"
                }
            )

            # Siklus Otomatis: Kirimkan template absen baru ke channel
            await message.channel.send(TEMPLATE_ABSEN_HINT)

    await bot.process_commands(message)

# 1. Fitur Intervensi Moderator Melalui Reaksi Silang (❌)
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return

    if str(payload.emoji) != "❌":
        return

    cfg = get_config()
    if payload.channel_id != cfg["absen_channel_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = payload.member or guild.get_member(payload.user_id)
    if not is_staff(member):
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        target_message = await channel.fetch_message(payload.message_id)
    except Exception as e:
        print(f"Gagal mengambil pesan target reaksi: {e}")
        return

    target_user = target_message.author
    if target_user.bot:
        return

    now_wib = datetime.now(WIB)
    today_str = now_wib.strftime("%Y-%m-%d")

    # Hapus dari database SQLite
    cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(target_user.id), today_str))
    conn.commit()

    # Hapus pesan absen yang disilang
    try:
        await target_message.delete()
    except Exception as e:
        print(f"Gagal menghapus pesan target: {e}")

    # Kirim pesan peringatan di channel absensi
    mod_mention_str = " ".join([f"<@&{r}>" for r in cfg["role_moderator_ids"]])
    await channel.send(
        f"⚠️ Absen milik {target_user.mention} dibatalkan oleh Moderator ({member.mention}) "
        f"karena foto tidak sesuai ketentuan. Silakan kirim ulang.\n{mod_mention_str}",
        delete_after=20
    )

    # Kirim Log ke Channel Audit Log
    await send_audit_log(
        guild,
        "🚫 Absen Dibatalkan oleh Moderator (Reaksi ❌)",
        f"Absen milik {target_user.mention} dibatalkan secara intervensi manual oleh {member.mention}.",
        color=discord.Color.dark_red(),
        fields={
            "Target Member": f"{target_user.name} ({target_user.id})",
            "Moderator": f"{member.name} ({member.id})",
            "Tanggal Dihapus": today_str,
            "Alasan": "Foto/bukti in-game dinilai tidak sesuai ketentuan dinas."
        }
    )

# 2. Command On-Demand: !rekap
@bot.command(name="rekap")
async def cmd_rekap(ctx):
    if not is_staff(ctx.author):
        await ctx.send("❌ Kamu tidak memiliki izin untuk melihat/memicu rekap absensi.", delete_after=10)
        return
    await ctx.send("⏳ Sedang menghitung dan menyusun rekapitulasi kehadiran mingguan...", delete_after=5)
    await run_weekly_recap(ctx.guild, target_channel=ctx.channel, is_manual=True)

# 3. Command Teguran Manual: !tegur @member [pesan]
@bot.command(name="tegur")
async def cmd_tegur(ctx, member: discord.Member, *, pesan: str = "Teguran kedisiplinan absensi dinas"):
    if not is_staff(ctx.author):
        await ctx.send("❌ Kamu tidak memiliki izin untuk memberikan teguran.", delete_after=10)
        return

    cfg = get_config()
    mod_mention_str = " ".join([f"<@&{r}>" for r in cfg["role_moderator_ids"]])

    # Kirim teguran resmi di channel
    embed = discord.Embed(
        title="⚠️ SURAT TEGURAN KEDISIPLINAN RESMI",
        description=(
            f"**Kepada:** {member.mention} (`{member.name}`)\n"
            f"**Oleh:** {ctx.author.mention}\n"
            f"**Catatan Pelanggaran:**\n```{pesan}```\n"
            f"Harap segera meningkatkan kedisiplinan absensi dinas sesuai PRD dan aturan kesatuan!"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(pytz.UTC)
    )
    embed.set_footer(text="Komando Disiplin PASPAMPRES")
    await ctx.send(content=f"{member.mention} {mod_mention_str}", embed=embed)

    # Catat ke audit log
    await send_audit_log(
        ctx.guild,
        "⚠️ Teguran Kedisiplinan Dikeluarkan",
        f"{ctx.author.mention} mengeluarkan teguran resmi untuk {member.mention}.",
        color=discord.Color.gold(),
        fields={
            "Personel Ditegur": f"{member.name} ({member.id})",
            "Pemberi Teguran": f"{ctx.author.name} ({ctx.author.id})",
            "Pesan": pesan
        }
    )

# 4. Command Override Absen: !override_absen @member tambah/kurang [YYYY-MM-DD]
@bot.command(name="override_absen")
async def cmd_override_absen(ctx, member: discord.Member, aksi: str, tanggal: str = None):
    if not is_staff(ctx.author):
        await ctx.send("❌ Kamu tidak memiliki izin untuk mengubah data absensi.", delete_after=10)
        return

    now_wib = datetime.now(WIB)
    target_date = tanggal if tanggal else now_wib.strftime("%Y-%m-%d")

    aksi_lower = aksi.lower()
    if aksi_lower in ["tambah", "add", "+"]:
        cursor.execute("INSERT OR REPLACE INTO attendance (user_id, date) VALUES (?, ?)", (str(member.id), target_date))
        conn.commit()
        await ctx.send(f"✅ Berhasil menambahkan kehadiran untuk {member.mention} pada tanggal `{target_date}`.")
        await send_audit_log(
            ctx.guild,
            "✏️ Override Absensi: Penambahan",
            f"{ctx.author.mention} menambahkan kehadiran manual untuk {member.mention}.",
            fields={"Tanggal": target_date, "Staff": ctx.author.name}
        )
    elif aksi_lower in ["kurang", "hapus", "remove", "-"]:
        cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(member.id), target_date))
        conn.commit()
        await ctx.send(f"🗑️ Berhasil menghapus kehadiran {member.mention} pada tanggal `{target_date}`.")
        await send_audit_log(
            ctx.guild,
            "✏️ Override Absensi: Pengurangan",
            f"{ctx.author.mention} menghapus kehadiran untuk {member.mention}.",
            fields={"Tanggal": target_date, "Staff": ctx.author.name}
        )
    else:
        await ctx.send("Format salah! Gunakan: `!override_absen @member [tambah/kurang] [YYYY-MM-DD]`")

# 5. Command Reject Manual: !reject @member [alasan]
@bot.command(name="reject")
async def cmd_reject(ctx, member: discord.Member, *, reason: str = "Foto atau data tidak sesuai ketentuan"):
    if not is_staff(ctx.author):
        await ctx.send("❌ Kamu tidak memiliki izin untuk menggunakan perintah ini.", delete_after=10)
        return

    cfg = get_config()
    now_wib = datetime.now(WIB)
    today_str = now_wib.strftime("%Y-%m-%d")

    cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(member.id), today_str))
    conn.commit()

    mod_mention_str = " ".join([f"<@&{r}>" for r in cfg["role_moderator_ids"]])
    absen_channel = bot.get_channel(cfg["absen_channel_id"]) or ctx.channel
    await absen_channel.send(
        f"⚠️ Absen milik {member.mention} dibatalkan oleh Moderator ({ctx.author.mention}) "
        f"karena: **{reason}**. Silakan kirim ulang.\n{mod_mention_str}"
    )

    await send_audit_log(
        ctx.guild,
        "🚫 Absen Dibatalkan via Perintah !reject",
        f"Absen milik {member.mention} dibatalkan oleh {ctx.author.mention}.",
        color=discord.Color.dark_red(),
        fields={
            "Target Member": f"{member.name} ({member.id})",
            "Moderator": f"{ctx.author.name} ({ctx.author.id})",
            "Tanggal": today_str,
            "Alasan": reason
        }
    )

# Perintah Manual untuk Admin: Test Pembukaan & Penutupan
@bot.command(name="buka_absen")
@commands.has_permissions(administrator=True)
async def cmd_buka_absen(ctx):
    await send_opening_announcement(ctx.channel)

@bot.command(name="tutup_absen")
@commands.has_permissions(administrator=True)
async def cmd_tutup_absen(ctx):
    await send_closing_announcement(ctx.channel)

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Error: DISCORD_BOT_TOKEN tidak ditemukan di environment variables.")

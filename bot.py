import discord
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, time
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
conn.commit()

# Role & Channel IDs
def get_config():
    return {
        "absen_channel_id": int(os.getenv("ABSEN_CHANNEL_ID", "0")),
        "role_wajib_absen_id": int(os.getenv("ROLE_WAJIB_ABSEN_ID", "0")),
        "log_channel_id": int(os.getenv("LOG_CHANNEL_ID", "0")),
        "role_moderator_ids": [
            int(r.strip()) for r in os.getenv("ROLE_MODERATOR_IDS", "1500812071024197682,1500811613794599022").split(",") if r.strip()
        ]
    }

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

# Jadwal Pembukaan Dinas (07:00 WIB / 00:00 UTC)
@tasks.loop(time=time(hour=0, minute=0, tzinfo=pytz.UTC))
async def schedule_opening():
    cfg = get_config()
    channel = bot.get_channel(cfg["absen_channel_id"])
    if channel:
        await send_opening_announcement(channel)

# Jadwal Penutupan Dinas (22:00 WIB / 15:00 UTC)
@tasks.loop(time=time(hour=15, minute=0, tzinfo=pytz.UTC))
async def schedule_closing():
    cfg = get_config()
    channel = bot.get_channel(cfg["absen_channel_id"])
    if channel:
        await send_closing_announcement(channel)

@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap mengamankan absensi sesuai PRD!")
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
            #     await send_audit_log(message.guild, "⚠️ Percobaan Absen Ganda", f"{message.author.mention} mencoba mengirim absen kedua kalinya hari ini.", color=discord.Color.gold())
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
    # Abaikan reaksi dari bot
    if payload.user_id == bot.user.id:
        return

    # Hanya berlaku untuk emoji silang (❌)
    if str(payload.emoji) != "❌":
        return

    cfg = get_config()
    if payload.channel_id != cfg["absen_channel_id"]:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = payload.member or guild.get_member(payload.user_id)
    if not member:
        return

    # Periksa apakah pemberi reaksi memiliki izin Admin atau Role Moderator/Pengawas
    is_admin = member.guild_permissions.administrator
    is_moderator = any(role.id in cfg["role_moderator_ids"] for role in member.roles)

    if not (is_admin or is_moderator):
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

    # Tanggal absensi berdasarkan waktu WIB saat ini
    now_wib = datetime.now(WIB)
    today_str = now_wib.strftime("%Y-%m-%d")

    # 1. Hapus dari database SQLite
    cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(target_user.id), today_str))
    conn.commit()

    # 2. Kirim pesan pemberitahuan di channel absensi
    mod_mention_str = " ".join([f"<@&{r}>" for r in cfg["role_moderator_ids"]])
    await channel.send(
        f"⚠️ Absen milik {target_user.mention} dibatalkan oleh Moderator ({member.mention}) "
        f"karena foto tidak sesuai ketentuan. Silakan kirim ulang.\n{mod_mention_str}"
    )

    # 3. Kirim Log ke Channel Audit Log
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

# 2. Perintah Manual Admin/Moderator: !reject @member [alasan]
@bot.command(name="reject")
async def cmd_reject(ctx, member: discord.Member, *, reason: str = "Foto atau data tidak sesuai ketentuan"):
    cfg = get_config()
    is_admin = ctx.author.guild_permissions.administrator
    is_moderator = any(role.id in cfg["role_moderator_ids"] for role in ctx.author.roles)

    if not (is_admin or is_moderator):
        await ctx.send("❌ Kamu tidak memiliki izin untuk menggunakan perintah ini.", delete_after=10)
        return

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

# Perintah Manual untuk Admin: Test Pembukaan (Buka & Pin)
@bot.command(name="buka_absen")
@commands.has_permissions(administrator=True)
async def cmd_buka_absen(ctx):
    await send_opening_announcement(ctx.channel)

# Perintah Manual untuk Admin: Test Penutupan
@bot.command(name="tutup_absen")
@commands.has_permissions(administrator=True)
async def cmd_tutup_absen(ctx):
    await send_closing_announcement(ctx.channel)

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Error: DISCORD_BOT_TOKEN tidak ditemukan di environment variables.")

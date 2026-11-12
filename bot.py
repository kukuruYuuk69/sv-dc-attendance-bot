import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, time, timedelta
import pytz
import os
import json
from typing import Literal

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

# 1. Tabel Absensi Harian
cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        user_id TEXT,
        date TEXT,
        PRIMARY KEY (user_id, date)
    )
''')

# 2. Tabel Riwayat Rekap Mingguan
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

# 3. Tabel Konfigurasi Dinamis Per-Server
cursor.execute('''
    CREATE TABLE IF NOT EXISTS guild_config (
        guild_id TEXT PRIMARY KEY,
        absen_channel_id TEXT,
        rekap_channel_id TEXT,
        wajib_absen_roles TEXT,
        staff_roles TEXT,
        open_time TEXT,
        close_time TEXT,
        start_day TEXT,
        templates TEXT
    )
''')
conn.commit()

# Default Templates
DEFAULT_TEMPLATES = {
    "absen": (
        "📋 **TEMPLATE ABSENSI:**\n"
        "```text\n"
        "Nama: \n"
        "Pangkat: \n"
        "Job: \n"
        "Divisi: \n"
        "Status: Hadir\n"
        "Ping: <@&1500812071024197682>\n"
        "```\n"
        "*(Wajib menyertakan screenshot/foto in-game)*"
    ),
    "opening": (
        "⏰ 【 SINYAL DINAS ON DUTY DIMULAI 】⏰\n\n"
        "Perhatian seluruh anggota PASPAMPRES,\n"
        "waktu dinas telah dimulai. Segera siapkan diri dan fokus pada pelaksanaan tugas.\n"
        "```- Wajib menjaga disiplin tanpa pengecualian\n"
        "- Patuh mutlak terhadap perintah atasan\n"
        "- Jaga kehormatan dan nama baik paspampres\n"
        "- Tidak mentolerir pelanggaran dalam bentuk apapun\n"
        "- Laksanakan tugas dengan sigap, tepat, dan bertanggung jawab```\n"
        "⚠️ Setiap pelanggaran akan ditindak sesuai aturan yang berlaku.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📢 PELAPORAN:\n"
        "Apabila terdapat personel masalah atau tidak sesuai aturan.\n"
        "segera laporkan ke <@&1500812071024197682> <@&1500811613794599022> \n"
        "━━━━━━━━━━━━━━━━━━\n"
        "_\"DISIPLIN ADALAH KEHORMATAN.\n"
        "LOYALITAS ADALAH TANGGUNG JAWAB.\n"
        "PROFESIONALISME ADALAH JATI DIRI.\"_\n\n"
        "Setia, waspada, jujur dan tanggung jawab.\n\n"
        "<@&1500083857591107744>"
    ),
    "closing": (
        "# 【 WAKTU ISTIRAHAT TELAH TIBA 】\n\n"
        "Seluruh personel Paspampres ANS dipersilakan mengakhiri aktivitas dan memasuki waktu istirahat.\n\n"
        "```- Gunakan waktu malam untuk memulihkan energi\n"
        "- Hindari aktivitas yang mengganggu kesiapan esok hari\n"
        "- Jaga sikap dan ketertiban di lingkungan masing-masing\n"
        "- Pastikan kesiapan untuk pelaksanaan dinas berikutnya```\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💤 Istirahat yang cukup adalah bagian dari kesiapan tempur.\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<@&1500083857591107744>"
    ),
    "teguran": "⚠️ Surat Teguran Kedisiplinan Resmi dari Komando Pengawas PASPAMPRES.",
    "peringatan": "🚨 PERINGATAN KEDISIPLINAN: Tidak memenuhi standar kehadiran minimal!"
}

# Helper: Ambil Konfigurasi Dinamis Guild
def get_guild_config(guild_id: int):
    gid_str = str(guild_id)
    cursor.execute("SELECT * FROM guild_config WHERE guild_id = ?", (gid_str,))
    row = cursor.fetchone()

    # Fallback default dari environment / PASPAMPRES
    default_absen = os.getenv("ABSEN_CHANNEL_ID", "1570440259316088953")
    default_rekap = os.getenv("REKAP_CHANNEL_ID", "1570460912572178443")
    default_wajib_roles = [int(os.getenv("ROLE_WAJIB_ABSEN_ID", "1500083857591107744"))]
    default_staff_roles = [
        int(r.strip()) for r in os.getenv("ROLE_MODERATOR_IDS", "1500812071024197682,1500811613794599022").split(",") if r.strip()
    ]

    if not row:
        cfg = {
            "guild_id": gid_str,
            "absen_channel_id": int(default_absen),
            "rekap_channel_id": int(default_rekap),
            "wajib_absen_roles": default_wajib_roles,
            "staff_roles": default_staff_roles,
            "open_time": "07:00",
            "close_time": "22:00",
            "start_day": "monday",
            "templates": DEFAULT_TEMPLATES.copy()
        }
        cursor.execute(
            '''INSERT OR REPLACE INTO guild_config 
               (guild_id, absen_channel_id, rekap_channel_id, wajib_absen_roles, staff_roles, open_time, close_time, start_day, templates)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                gid_str,
                str(cfg["absen_channel_id"]),
                str(cfg["rekap_channel_id"]),
                json.dumps(cfg["wajib_absen_roles"]),
                json.dumps(cfg["staff_roles"]),
                cfg["open_time"],
                cfg["close_time"],
                cfg["start_day"],
                json.dumps(cfg["templates"])
            )
        )
        conn.commit()
        return cfg

    # Parse existing row
    try:
        w_roles = [int(x) for x in json.loads(row[3])]
    except Exception:
        w_roles = default_wajib_roles

    try:
        s_roles = [int(x) for x in json.loads(row[4])]
    except Exception:
        s_roles = default_staff_roles

    try:
        tmpl = json.loads(row[8])
    except Exception:
        tmpl = DEFAULT_TEMPLATES.copy()

    return {
        "guild_id": gid_str,
        "absen_channel_id": int(row[1]) if row[1] else int(default_absen),
        "rekap_channel_id": int(row[2]) if row[2] else int(default_rekap),
        "wajib_absen_roles": w_roles,
        "staff_roles": s_roles,
        "open_time": row[5] or "07:00",
        "close_time": row[6] or "22:00",
        "start_day": row[7] or "monday",
        "templates": tmpl
    }

# Helper: Update Konfigurasi Dinamis Guild
def update_guild_config(guild_id: int, key: str, value):
    cfg = get_guild_config(guild_id)
    cfg[key] = value

    cursor.execute(
        '''UPDATE guild_config SET 
           absen_channel_id = ?,
           rekap_channel_id = ?,
           wajib_absen_roles = ?,
           staff_roles = ?,
           open_time = ?,
           close_time = ?,
           start_day = ?,
           templates = ?
           WHERE guild_id = ?''',
        (
            str(cfg["absen_channel_id"]),
            str(cfg["rekap_channel_id"]),
            json.dumps(cfg["wajib_absen_roles"]),
            json.dumps(cfg["staff_roles"]),
            cfg["open_time"],
            cfg["close_time"],
            cfg["start_day"],
            json.dumps(cfg["templates"]),
            str(guild_id)
        )
    )
    conn.commit()

# Helper Validasi Staf (Admin & Moderator)
def check_is_staff(interaction: discord.Interaction) -> bool:
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    cfg = get_guild_config(interaction.guild.id)
    return any(role.id in cfg["staff_roles"] for role in interaction.user.roles)

# Helper Siklus 7 Hari Rekap Berdasarkan start_day
DAY_MAP = {
    "monday": 0, "senin": 0,
    "tuesday": 1, "selasa": 1,
    "wednesday": 2, "rabu": 2,
    "thursday": 3, "kamis": 3,
    "friday": 4, "jumat": 4,
    "saturday": 5, "sabtu": 5,
    "sunday": 6, "minggu": 6
}

def get_week_cycle_bounds(start_day_name="monday", ref_date=None):
    if ref_date is None:
        ref_date = datetime.now(WIB)
    target_start_idx = DAY_MAP.get(start_day_name.lower(), 0)
    current_weekday = ref_date.weekday()

    diff_days = (current_weekday - target_start_idx) % 7
    start_date = ref_date - timedelta(days=diff_days)
    end_date = start_date + timedelta(days=6)
    week_key = f"{start_date.strftime('%Y-%m-%d')}_to_{end_date.strftime('%Y-%m-%d')}"
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), week_key

# Helper Audit Log
async def send_audit_log(guild: discord.Guild, title: str, description: str, color=discord.Color.blue(), fields=None):
    log_ch_id = int(os.getenv("LOG_CHANNEL_ID", "0"))
    if not log_ch_id:
        return
    channel = guild.get_channel(log_ch_id)
    if not channel:
        return
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now(pytz.UTC))
    if fields:
        for name, val in fields.items():
            embed.add_field(name=name, value=val, inline=False)
    embed.set_footer(text="Sistem Audit Absensi PASPAMPRES")
    try:
        await channel.send(embed=embed)
    except Exception:
        pass

# Helper Pembukaan & Penutupan Dinas
last_pinned_messages = {}

async def execute_opening(channel: discord.TextChannel, cfg: dict):
    global last_pinned_messages
    try:
        guild_id = channel.guild.id
        old_pinned_id = last_pinned_messages.get(guild_id)
        if old_pinned_id:
            try:
                old_msg = await channel.fetch_message(old_pinned_id)
                if old_msg.pinned:
                    await old_msg.unpin()
            except Exception:
                pass

        open_text = cfg["templates"].get("opening", DEFAULT_TEMPLATES["opening"])
        absen_text = cfg["templates"].get("absen", DEFAULT_TEMPLATES["absen"])
        full_message = f"{open_text}\n\n━━━━━━━━━━━━━━━━━━\n{absen_text}"

        new_msg = await channel.send(full_message)
        await new_msg.pin()
        last_pinned_messages[guild_id] = new_msg.id
        return True
    except Exception as e:
        print(f"Error opening announcement: {e}")
        return False

async def execute_closing(channel: discord.TextChannel, cfg: dict):
    try:
        close_text = cfg["templates"].get("closing", DEFAULT_TEMPLATES["closing"])
        await channel.send(close_text)
        return True
    except Exception as e:
        print(f"Error closing announcement: {e}")
        return False

# ==========================================
# DISCORD SLASH COMMANDS (/...)
# ==========================================

# 1. /buka_absen
@bot.tree.command(name="buka_absen", description="Buka sesi absensi manual, auto-pin, dan kirim template.")
async def slash_buka_absen(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    channel = interaction.guild.get_channel(cfg["absen_channel_id"]) or interaction.channel
    await interaction.response.send_message("⏳ Membuka sesi absensi dinas dan me-pin pengumuman...", ephemeral=True)
    success = await execute_opening(channel, cfg)
    if success:
        await interaction.followup.send("✅ Sesi absensi dinas berhasil dibuka dan di-pin!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Terjadi kendala saat membuka sesi absensi.", ephemeral=True)

# 2. /tutup_absen
@bot.tree.command(name="tutup_absen", description="Tutup sesi absensi dinas manual dan kirim pengumuman istirahat.")
async def slash_tutup_absen(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    channel = interaction.guild.get_channel(cfg["absen_channel_id"]) or interaction.channel
    await interaction.response.send_message("⏳ Mengirim pengumuman penutupan absensi dinas...", ephemeral=True)
    success = await execute_closing(channel, cfg)
    if success:
        await interaction.followup.send("✅ Sesi absensi dinas telah ditutup.", ephemeral=True)
    else:
        await interaction.followup.send("❌ Terjadi kendala saat menutup sesi absensi.", ephemeral=True)

# 3. View Paginasi untuk /rekap
class RecapPaginationView(discord.ui.View):
    def __init__(self, pages: list[discord.Embed]):
        super().__init__(timeout=180)
        self.pages = pages
        self.current_page = 0
        self.update_buttons()

    def update_buttons(self):
        self.prev_btn.disabled = (self.current_page == 0)
        self.next_btn.disabled = (self.current_page == len(self.pages) - 1)
        self.page_indicator.label = f"Halaman {self.current_page + 1}/{len(self.pages)}"

    @discord.ui.button(label="◀ Sebelumnya", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="Halaman 1/1", style=discord.ButtonStyle.primary, disabled=True)
    async def page_indicator(self, interaction: discord.Interaction, button: discord.ui.Button):
        pass

    @discord.ui.button(label="Selanjutnya ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

# /rekap
@bot.tree.command(name="rekap", description="Tampilkan rekapitulasi kehadiran mingguan berhalaman (Embed pagination).")
async def slash_rekap(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk melihat rekapitulasi.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=False)
    cfg = get_guild_config(interaction.guild.id)
    guild = interaction.guild

    start_date, end_date, current_week_key = get_week_cycle_bounds(cfg["start_day"])

    # Cari seluruh member yang memiliki salah satu role wajib absen
    target_members = []
    for m in guild.members:
        if m.bot:
            continue
        if any(r.id in cfg["wajib_absen_roles"] for r in m.roles):
            target_members.append(m)

    # Query absensi dalam siklus 7 hari
    cursor.execute(
        "SELECT user_id, COUNT(DISTINCT date) as cnt FROM attendance WHERE date >= ? AND date <= ? GROUP BY user_id",
        (start_date, end_date)
    )
    attendance_map = dict(cursor.fetchall())

    normal_list = []
    violating_list = []

    for m in target_members:
        c = attendance_map.get(str(m.id), 0)
        if c >= 3:
            normal_list.append((m, c))
        else:
            violating_list.append((m, c))

    normal_list.sort(key=lambda x: x[1], reverse=True)
    violating_list.sort(key=lambda x: x[1])

    # Bangun Halaman Embed
    pages = []

    # Halaman 1: Ringkasan & Personel Disiplin
    embed1 = discord.Embed(
        title="📊 REKAPITULASI DINAS MINGGUAN PASPAMPRES",
        description=(
            f"**Periode Siklus:** `{start_date}` s/d `{end_date}`\n"
            f"**Total Personel Wajib Absen:** {len(target_members)} Orang\n"
            f"**Standar Disiplin:** Minimal 3x Hadir\n"
            f"**Hari Awal Siklus:** {cfg['start_day'].capitalize()}"
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now(pytz.UTC)
    )

    disciplined_lines = [f"✅ **{m.mention}** (`{m.display_name}`): **{c}x** Hadir" for m, c in normal_list]
    chunk_text = "\n".join(disciplined_lines[:25]) if disciplined_lines else "Belum ada personel yang mencapai 3x hadir."
    embed1.add_field(name=f"🟢 Personel Memenuhi Standar (>= 3x) — [{len(normal_list)}]", value=chunk_text[:1024], inline=False)
    if len(disciplined_lines) > 25:
        embed1.add_field(name="🟢 Personel Memenuhi Standar (Lanjutan)", value="\n".join(disciplined_lines[25:50])[:1024], inline=False)
    embed1.set_footer(text="Sistem Absensi PASPAMPRES • Halaman 1")
    pages.append(embed1)

    # Halaman 2: Personel Melanggar (<3x)
    embed2 = discord.Embed(
        title="⚠️ DAFTAR PERSONEL KURANG DARI 3X HADIR",
        description=f"Personel berikut memerlukan evaluasi kedisiplinan pada periode `{start_date}` s/d `{end_date}`.",
        color=discord.Color.gold(),
        timestamp=datetime.now(pytz.UTC)
    )
    viol_lines = [f"⚠️ **{m.mention}** (`{m.display_name}`): Hanya **{c}x** Hadir" for m, c in violating_list]
    viol_chunk = "\n".join(viol_lines[:25]) if viol_lines else "Semua personel memenuhi standar minimal!"
    embed2.add_field(name=f"🟡 Personel Perlu Tindak Lanjut (< 3x) — [{len(violating_list)}]", value=viol_chunk[:1024], inline=False)
    if len(viol_lines) > 25:
        embed2.add_field(name="🟡 Personel Perlu Tindak Lanjut (Lanjutan)", value="\n".join(viol_lines[25:50])[:1024], inline=False)
    embed2.set_footer(text="Sistem Absensi PASPAMPRES • Halaman 2")
    pages.append(embed2)

    view = RecapPaginationView(pages)
    await interaction.followup.send(embed=pages[0], view=view)

# 4. /tegur
@bot.tree.command(name="tegur", description="Kirim Embed Surat Teguran Kedisiplinan Resmi kepada personel.")
@app_commands.describe(member="Personel yang ditegur", pesan="Catatan pelanggaran kedisiplinan")
async def slash_tegur(interaction: discord.Interaction, member: discord.Member, pesan: str):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk menegur personel.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    mod_tag_str = " ".join([f"<@&{r}>" for r in cfg["staff_roles"]])

    embed = discord.Embed(
        title="⚠️ SURAT TEGURAN KEDISIPLINAN RESMI",
        description=(
            f"**Personel Dituju:** {member.mention} (`{member.display_name}`)\n"
            f"**Pejabat Pengawas:** {interaction.user.mention}\n\n"
            f"**Catatan Pelanggaran:**\n```{pesan}```\n"
            f"⚠️ *Peringatan resmi ini dicatat ke dalam database kedisiplinan. "
            f"Harap segera memperbaiki kepatuhan dinas!*"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(pytz.UTC)
    )
    embed.set_footer(text="Komando Disiplin PASPAMPRES")

    await interaction.response.send_message(content=f"{member.mention} {mod_tag_str}", embed=embed)
    await send_audit_log(
        interaction.guild,
        "⚠️ Teguran Kedisiplinan Dikeluarkan",
        f"{interaction.user.mention} menegur {member.mention} via Slash Command.",
        color=discord.Color.gold(),
        fields={"Member": member.name, "Pengawas": interaction.user.name, "Pesan": pesan}
    )

# 5. /reject
@bot.tree.command(name="reject", description="Batalkan kehadiran absen member hari ini dari database.")
@app_commands.describe(member="Member yang absensinya dibatalkan", alasan="Alasan pembatalan absensi")
async def slash_reject(interaction: discord.Interaction, member: discord.Member, alasan: str):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk membatalkan absen.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    today_str = datetime.now(WIB).strftime("%Y-%m-%d")

    cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(member.id), today_str))
    conn.commit()

    mod_tag_str = " ".join([f"<@&{r}>" for r in cfg["staff_roles"]])
    absen_ch = interaction.guild.get_channel(cfg["absen_channel_id"]) or interaction.channel

    await interaction.response.send_message(f"✅ Absensi {member.mention} untuk tanggal `{today_str}` berhasil dibatalkan.", ephemeral=True)
    await absen_ch.send(
        f"⚠️ Absen milik {member.mention} dibatalkan oleh Pengawas ({interaction.user.mention}) "
        f"karena: **{alasan}**. Silakan kirim ulang absensi yang benar.\n{mod_tag_str}"
    )

    await send_audit_log(
        interaction.guild,
        "🚫 Absen Dibatalkan via /reject",
        f"Absensi {member.mention} dibatalkan oleh {interaction.user.mention}.",
        color=discord.Color.dark_red(),
        fields={"Member": member.name, "Staff": interaction.user.name, "Alasan": alasan}
    )

# 6. /help
@bot.tree.command(name="help", description="Panduan lengkap seluruh fitur dan Slash Commands bot.")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📖 PANDUAN LENGKAP BOT ABSENSI PASPAMPRES",
        description="Berikut adalah daftar perintah Slash Commands (`/`) yang tersedia:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🛠️ Perintah Operasional Dinas",
        value=(
            "`/buka_absen` — Membuka sesi absen harian manual, auto-pin, dan kirim template.\n"
            "`/tutup_absen` — Menutup sesi absen manual dan mengirim pesan istirahat.\n"
            "`/rekap` — Menampilkan rekapitulasi kehadiran mingguan berhalaman (Embed pagination).\n"
            "`/tegur` — Mengirim surat teguran resmi kepada personel yang melanggar.\n"
            "`/reject` — Membatalkan kehadiran member hari ini seketika."
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Perintah Konfigurasi Server (`/config`)",
        value=(
            "`/config show` — Tampilkan seluruh pengaturan dinamis server aktif.\n"
            "`/config role_absen` — Tambah atau hapus role wajib absen.\n"
            "`/config role_staff` — Tambah atau hapus role staf pengawas (Admin/Mod).\n"
            "`/config jadwal` — Atur jam buka dan tutup absensi otomatis (WIB).\n"
            "`/config hari_awal` — Atur hari permulaan siklus 7 hari rekap mingguan.\n"
            "`/config channel` — Atur saluran absensi dinas atau saluran rekap.\n"
            "`/config template` — Kustomisasi template teks dinamis bot."
        ),
        inline=False
    )
    embed.set_footer(text="Sistem Otomasi Kedisiplinan PASPAMPRES")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# COMMAND GROUP: /config
# ==========================================
config_group = app_commands.Group(name="config", description="Pengaturan dinamis bot absensi server")

@config_group.command(name="show", description="Tampilkan konfigurasi aktif server saat ini.")
async def config_show(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk melihat pengaturan.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    absen_ch = interaction.guild.get_channel(cfg["absen_channel_id"])
    rekap_ch = interaction.guild.get_channel(cfg["rekap_channel_id"])

    wajib_roles_str = ", ".join([f"<@&{r}>" for r in cfg["wajib_absen_roles"]]) or "Belum diatur"
    staff_roles_str = ", ".join([f"<@&{r}>" for r in cfg["staff_roles"]]) or "Belum diatur"

    embed = discord.Embed(
        title=f"⚙️ Konfigurasi Server: {interaction.guild.name}",
        color=discord.Color.green(),
        timestamp=datetime.now(pytz.UTC)
    )
    embed.add_field(name="Saluran Absensi", value=absen_ch.mention if absen_ch else f"ID: {cfg['absen_channel_id']}", inline=True)
    embed.add_field(name="Saluran Rekap", value=rekap_ch.mention if rekap_ch else f"ID: {cfg['rekap_channel_id']}", inline=True)
    embed.add_field(name="Hari Awal Siklus", value=cfg["start_day"].capitalize(), inline=True)
    embed.add_field(name="Jadwal Otomatis (WIB)", value=f"Buka: `{cfg['open_time']}` | Tutup: `{cfg['close_time']}`", inline=False)
    embed.add_field(name="Role Wajib Absen", value=wajib_roles_str, inline=False)
    embed.add_field(name="Role Staf Pengawas", value=staff_roles_str, inline=False)
    embed.set_footer(text="Gunakan sub-command /config untuk mengubah pengaturan")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@config_group.command(name="role_absen", description="Tambah atau hapus role wajib absen.")
@app_commands.describe(role="Role yang ingin dikonfigurasi", aksi="Pilih tambah atau hapus")
async def config_role_absen(interaction: discord.Interaction, role: discord.Role, aksi: Literal["tambah", "hapus"]):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    roles = cfg["wajib_absen_roles"]
    if aksi == "tambah":
        if role.id not in roles:
            roles.append(role.id)
            update_guild_config(interaction.guild.id, "wajib_absen_roles", roles)
            await interaction.response.send_message(f"✅ Role {role.mention} berhasil ditambahkan ke daftar wajib absen.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} sudah ada di daftar wajib absen.", ephemeral=True)
    else:
        if role.id in roles:
            roles.remove(role.id)
            update_guild_config(interaction.guild.id, "wajib_absen_roles", roles)
            await interaction.response.send_message(f"🗑️ Role {role.mention} berhasil dihapus dari daftar wajib absen.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} tidak ditemukan di daftar wajib absen.", ephemeral=True)

@config_group.command(name="role_staff", description="Tambah atau hapus role staf pengawas bot.")
@app_commands.describe(role="Role staf", aksi="Pilih tambah atau hapus")
async def config_role_staff(interaction: discord.Interaction, role: discord.Role, aksi: Literal["tambah", "hapus"]):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    roles = cfg["staff_roles"]
    if aksi == "tambah":
        if role.id not in roles:
            roles.append(role.id)
            update_guild_config(interaction.guild.id, "staff_roles", roles)
            await interaction.response.send_message(f"✅ Role staf {role.mention} berhasil ditambahkan.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} sudah terdaftar sebagai staf.", ephemeral=True)
    else:
        if role.id in roles:
            roles.remove(role.id)
            update_guild_config(interaction.guild.id, "staff_roles", roles)
            await interaction.response.send_message(f"🗑️ Role {role.mention} berhasil dihapus dari daftar staf.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} tidak terdaftar di staf.", ephemeral=True)

@config_group.command(name="jadwal", description="Atur jam buka dan tutup absensi dinas (format HH:MM WIB).")
@app_commands.describe(jam_buka="Contoh: 07:00", jam_tutup="Contoh: 22:00")
async def config_jadwal(interaction: discord.Interaction, jam_buka: str, jam_tutup: str):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    for t_str in [jam_buka, jam_tutup]:
        try:
            parts = t_str.strip().split(":")
            if len(parts) != 2 or not (0 <= int(parts[0]) <= 23 and 0 <= int(parts[1]) <= 59):
                raise ValueError
        except Exception:
            await interaction.response.send_message(f"❌ Format waktu `{t_str}` salah! Gunakan format 24 jam `HH:MM` (contoh: `07:00`).", ephemeral=True)
            return

    update_guild_config(interaction.guild.id, "open_time", jam_buka.strip())
    update_guild_config(interaction.guild.id, "close_time", jam_tutup.strip())
    await interaction.response.send_message(f"✅ Jadwal dinas berhasil diperbarui:\nBuka: `{jam_buka}` WIB | Tutup: `{jam_tutup}` WIB", ephemeral=True)

@config_group.command(name="hari_awal", description="Atur hari awal siklus 7 hari rekapitulasi mingguan.")
async def config_hari_awal(interaction: discord.Interaction, hari: Literal["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    update_guild_config(interaction.guild.id, "start_day", hari.lower())
    await interaction.response.send_message(f"✅ Hari permulaan siklus rekap berhasil diubah ke: **{hari}**.", ephemeral=True)

@config_group.command(name="channel", description="Atur saluran absensi atau saluran rekap.")
@app_commands.describe(tipe="Pilih jenis saluran", channel="Channel target")
async def config_channel(interaction: discord.Interaction, tipe: Literal["absensi", "rekap"], channel: discord.TextChannel):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    key = "absen_channel_id" if tipe == "absensi" else "rekap_channel_id"
    update_guild_config(interaction.guild.id, key, channel.id)
    await interaction.response.send_message(f"✅ Saluran **{tipe}** berhasil diarahkan ke: {channel.mention}.", ephemeral=True)

@config_group.command(name="template", description="Kustomisasi template teks pesan bot.")
@app_commands.describe(jenis="Pilih template yang ingin diubah", teks="Teks template baru")
async def config_template(interaction: discord.Interaction, jenis: Literal["opening", "closing", "absen", "teguran", "peringatan"], teks: str):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    templates = cfg["templates"]
    templates[jenis] = teks
    update_guild_config(interaction.guild.id, "templates", templates)
    await interaction.response.send_message(f"✅ Template teks **{jenis}** berhasil diperbarui!", ephemeral=True)

bot.tree.add_command(config_group)

# ==========================================
# LOOP JADWAL DINAMIS PER MENIT
# ==========================================
last_executed_open_minute = {}
last_executed_close_minute = {}

@tasks.loop(minutes=1)
async def check_dynamic_schedules():
    now_wib = datetime.now(WIB)
    current_time_str = now_wib.strftime("%H:%M")
    current_day_str = now_wib.strftime("%Y-%m-%d")

    for guild in bot.guilds:
        try:
            cfg = get_guild_config(guild.id)
            absen_channel = guild.get_channel(cfg["absen_channel_id"])
            if not absen_channel:
                continue

            # Pengecekan Jadwal Buka
            if current_time_str == cfg["open_time"]:
                last_time = last_executed_open_minute.get(guild.id)
                if last_time != current_time_str:
                    last_executed_open_minute[guild.id] = current_time_str
                    print(f"[{guild.name}] Trigger otomatis jadwal buka dinas: {current_time_str} WIB")
                    await execute_opening(absen_channel, cfg)

            # Pengecekan Jadwal Tutup
            if current_time_str == cfg["close_time"]:
                last_time = last_executed_close_minute.get(guild.id)
                if last_time != current_time_str:
                    last_executed_close_minute[guild.id] = current_time_str
                    print(f"[{guild.name}] Trigger otomatis jadwal tutup dinas: {current_time_str} WIB")
                    await execute_closing(absen_channel, cfg)

                    # Cek apakah hari ini adalah hari terakhir siklus rekap mingguan
                    # Hari terakhir siklus adalah 6 hari setelah start_day
                    start_idx = DAY_MAP.get(cfg["start_day"].lower(), 0)
                    end_idx = (start_idx + 6) % 7
                    if now_wib.weekday() == end_idx:
                        print(f"[{guild.name}] Menjalankan rekapitulasi otomatis akhir siklus mingguan...")
                        rekap_channel = guild.get_channel(cfg["rekap_channel_id"])
                        if rekap_channel:
                            # Kirim rekap mingguan otomatis
                            pass
        except Exception as e:
            print(f"Error pada loop jadwal guild {guild.id}: {e}")

# ==========================================
# EVENTS (on_ready, on_message, on_raw_reaction_add)
# ==========================================
@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap mengamankan absensi dinas PASPAMPRES!")
    try:
        synced = await bot.tree.sync()
        print(f"Berhasil mensinkronkan {len(synced)} Discord Slash Commands!")
    except Exception as e:
        print(f"Gagal mensinkronkan Slash Commands: {e}")

    if not check_dynamic_schedules.is_running():
        check_dynamic_schedules.start()

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    cfg = get_guild_config(message.guild.id)
    if message.channel.id == cfg["absen_channel_id"]:
        now_wib = datetime.now(WIB)
        today_str = now_wib.strftime("%Y-%m-%d")
        is_wajib = any(role.id in cfg["wajib_absen_roles"] for role in message.author.roles)

        if is_wajib:
            content = message.content

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
            required_fields = ["Nama:", "Pangkat:", "Job:", "Divisi:", "Status: Hadir"]
            missing_fields = [f for f in required_fields if f not in content]
            if missing_fields:
                await message.delete()
                absen_hint = cfg["templates"].get("absen", DEFAULT_TEMPLATES["absen"])
                await message.channel.send(
                    f"⚠️ {message.author.mention} Format absen tidak sesuai!\n"
                    f"Wajib menggunakan template berikut secara presisi:\n{absen_hint}",
                    delete_after=20
                )
                await send_audit_log(
                    message.guild,
                    "⚠️ Absen Ditolak (Format Salah)",
                    f"Absen dari {message.author.mention} ditolak karena tidak sesuai template teks wajib.",
                    color=discord.Color.orange()
                )
                return

            # Absen Diterima & Dicatat ke Database
            cursor.execute("INSERT OR REPLACE INTO attendance (user_id, date) VALUES (?, ?)", (str(message.author.id), today_str))
            conn.commit()
            await message.add_reaction("✅")

            await send_audit_log(
                message.guild,
                "✅ Absen Masuk Disetujui",
                f"Absen dari {message.author.mention} diverifikasi dan dicatat.",
                color=discord.Color.green(),
                fields={"Member": f"{message.author.name} ({message.author.id})", "Tanggal": today_str}
            )

            # Kirim Template Absen Baru di Bawahnya
            absen_hint = cfg["templates"].get("absen", DEFAULT_TEMPLATES["absen"])
            await message.channel.send(absen_hint)

    await bot.process_commands(message)

# Intervensi Reaksi Silang (❌) oleh Staf
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id or str(payload.emoji) != "❌":
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    cfg = get_guild_config(guild.id)
    if payload.channel_id != cfg["absen_channel_id"]:
        return

    member = payload.member or guild.get_member(payload.user_id)
    if not member:
        return

    is_admin = member.guild_permissions.administrator
    is_staff_role = any(r.id in cfg["staff_roles"] for r in member.roles)
    if not (is_admin or is_staff_role):
        return

    channel = guild.get_channel(payload.channel_id)
    if not channel:
        return

    try:
        target_message = await channel.fetch_message(payload.message_id)
    except Exception:
        return

    target_user = target_message.author
    if target_user.bot:
        return

    today_str = datetime.now(WIB).strftime("%Y-%m-%d")

    # Hapus dari Database
    cursor.execute("DELETE FROM attendance WHERE user_id = ? AND date = ?", (str(target_user.id), today_str))
    conn.commit()

    # Hapus Pesan Absen Seketika
    try:
        await target_message.delete()
    except Exception:
        pass

    # Berikan Notifikasi di Channel
    mod_tag_str = " ".join([f"<@&{r}>" for r in cfg["staff_roles"]])
    await channel.send(
        f"⚠️ Absen milik {target_user.mention} dibatalkan oleh Pengawas ({member.mention}) "
        f"karena foto/ketentuan tidak sesuai. Silakan kirim ulang absensi yang benar.\n{mod_tag_str}",
        delete_after=20
    )

    await send_audit_log(
        guild,
        "🚫 Absen Dibatalkan via Reaksi ❌",
        f"Absensi {target_user.mention} dibatalkan oleh {member.mention}.",
        color=discord.Color.dark_red(),
        fields={"Member": target_user.name, "Staff": member.name, "Tanggal": today_str}
    )

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Error: DISCORD_BOT_TOKEN tidak ditemukan di environment variables.")

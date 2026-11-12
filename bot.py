import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, time, timedelta
import pytz
import os
import json
import re
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
        templates TEXT,
        ping_role_id TEXT,
        ping_roles TEXT
    )
''')
conn.commit()

# Pastikan kolom ping_roles ada
try:
    cursor.execute("ALTER TABLE guild_config ADD COLUMN ping_roles TEXT")
    conn.commit()
except Exception:
    pass

# Default Universal Agnostic Templates
DEFAULT_TEMPLATES = {
    "absen_fields": (
        "Nama: \n"
        "Divisi: \n"
        "Status: Hadir\n"
        "Ping: {ping_roles_mentions}"
    ),
    "opening": (
        "⏰ 【 SESI ABSENSI HARIAN DIMULAI 】⏰\n\n"
        "Perhatian seluruh anggota,\n"
        "Sesi absensi dan dinas telah dibuka. Segera lengkapi presensi kehadiran sesuai ketentuan.\n"
        "```- Pastikan melampirkan screenshot / bukti kehadiran\n"
        "- Gunakan template presensi yang ditentukan\n"
        "- Laporkan kendala langsung kepada staf pengawas```\n"
        "⚠️ Harap menjaga kedisiplinan dan ketertiban bersama."
    ),
    "closing": (
        "# 【 SESI ABSENSI HARIAN TELAH BERAKHIR 】\n\n"
        "Sesi absensi hari ini telah resmi ditutup.\n\n"
        "```- Terima kasih atas partisipasi dan kedisiplinan Anda hari ini\n"
        "- Pastikan kesiapan untuk jadwal dinas berikutnya```\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💤 Istirahat yang cukup untuk menjaga produktivitas."
    ),
    "teguran": "⚠️ Surat Teguran Kedisiplinan Resmi dari Staf Pengawas.",
    "peringatan": "🚨 PERINGATAN KEDISIPLINAN: Belum memenuhi standar kehadiran minimal!"
}

# Helper: Ambil Konfigurasi Dinamis Guild
def get_guild_config(guild_id: int):
    gid_str = str(guild_id)
    cursor.execute("SELECT * FROM guild_config WHERE guild_id = ?", (gid_str,))
    row = cursor.fetchone()

    # Fallback default murni agnostik (tidak ada hardcode ID role)
    default_absen = os.getenv("ABSEN_CHANNEL_ID", "0")
    default_rekap = os.getenv("REKAP_CHANNEL_ID", "0")
    default_wajib_roles = [int(os.getenv("ROLE_WAJIB_ABSEN_ID"))] if os.getenv("ROLE_WAJIB_ABSEN_ID") else []
    default_staff_roles = [
        int(r.strip()) for r in os.getenv("ROLE_MODERATOR_IDS", "").split(",") if r.strip()
    ]
    default_ping_roles = []

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
            "templates": DEFAULT_TEMPLATES.copy(),
            "ping_role_id": None,
            "ping_roles": default_ping_roles
        }
        cursor.execute(
            '''INSERT OR REPLACE INTO guild_config 
               (guild_id, absen_channel_id, rekap_channel_id, wajib_absen_roles, staff_roles, open_time, close_time, start_day, templates, ping_role_id, ping_roles)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                gid_str,
                str(cfg["absen_channel_id"]),
                str(cfg["rekap_channel_id"]),
                json.dumps(cfg["wajib_absen_roles"]),
                json.dumps(cfg["staff_roles"]),
                cfg["open_time"],
                cfg["close_time"],
                cfg["start_day"],
                json.dumps(cfg["templates"]),
                "",
                json.dumps(cfg["ping_roles"])
            )
        )
        conn.commit()
        return cfg

    # Parse JSON kolom
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

    # Parse ping_roles (multi-role)
    p_roles = []
    if len(row) > 10 and row[10]:
        try:
            p_roles = [int(x) for x in json.loads(row[10])]
        except Exception:
            p_roles = []
    elif len(row) > 9 and row[9] and row[9].strip() and row[9].strip() != "None":
        try:
            p_roles = [int(row[9])]
        except Exception:
            p_roles = []

    return {
        "guild_id": gid_str,
        "absen_channel_id": int(row[1]) if row[1] else int(default_absen),
        "rekap_channel_id": int(row[2]) if row[2] else int(default_rekap),
        "wajib_absen_roles": w_roles,
        "staff_roles": s_roles,
        "open_time": row[5] or "07:00",
        "close_time": row[6] or "22:00",
        "start_day": row[7] or "monday",
        "templates": tmpl,
        "ping_roles": p_roles
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
           templates = ?,
           ping_roles = ?
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
            json.dumps(cfg["ping_roles"]),
            str(guild_id)
        )
    )
    conn.commit()

# Helper: Render Mentions Multi-Role
def get_ping_roles_mentions(ping_roles: list[int]) -> str:
    if not ping_roles:
        return ""
    return " ".join([f"<@&{r}>" for r in ping_roles])

# Helper: Render Template Absensi dengan Header, Code Block, dan Footer
def render_attendance_template(cfg: dict) -> str:
    ping_roles = cfg.get("ping_roles", [])
    ping_mentions = get_ping_roles_mentions(ping_roles)
    tmpl = cfg.get("templates", {})

    custom_absen = tmpl.get("absen")
    if isinstance(custom_absen, dict):
        fields_str = custom_absen.get("teks", "")
    elif isinstance(custom_absen, str):
        fields_str = custom_absen
    elif "absen_fields" in tmpl:
        fields_str = tmpl["absen_fields"]
    else:
        fields_str = (
            "Nama: \n"
            "Divisi: \n"
            "Status: Hadir\n"
            f"Ping: {ping_mentions}".strip()
        )

    # Ganti placeholder multi-role jika ada
    if "{ping_roles_mentions}" in fields_str:
        fields_str = fields_str.replace("{ping_roles_mentions}", ping_mentions)
    elif "{ping_role_id}" in fields_str:
        fields_str = fields_str.replace("{ping_role_id}", str(ping_roles[0]) if ping_roles else "")

    # Bersihkan markdown backtick
    clean_fields = fields_str.replace("```text", "").replace("```", "").strip()

    # Hapus header/footer duplikat jika teks input user menyertakannya
    clean_lines = []
    for line in clean_fields.splitlines():
        l_strip = line.strip()
        if "TEMPLATE ABSENSI" in l_strip.upper() or "ATTENDANCE TEMPLATE" in l_strip.upper():
            continue
        if "WAJIB MENYERTAKAN SCREENSHOT" in l_strip.upper() or "BUKTI KEHADIRAN" in l_strip.upper():
            continue
        # Jika baris adalah Ping dan tidak ada role yang didaftarkan, cetak 'Ping: ' bersih tanpa tag
        if l_strip.lower().startswith("ping:"):
            if ping_mentions:
                clean_lines.append(f"Ping: {ping_mentions}")
            else:
                clean_lines.append("Ping: ")
            continue
        clean_lines.append(line)
    body_content = "\n".join(clean_lines).strip()

    # Jika belum ada baris ping sama sekali, tambahkan baris ping
    if "ping:" not in body_content.lower():
        if ping_mentions:
            body_content += f"\nPing: {ping_mentions}"
        else:
            body_content += "\nPing: "

    # Susun 3 bagian konsisten: Header, Code Block, Footer
    rendered = (
        "📋 **TEMPLATE ABSENSI:**\n"
        "```text\n"
        f"{body_content}\n"
        "```\n"
        "*(Wajib menyertakan screenshot/foto in-game/bukti kehadiran)*"
    )
    return rendered

# Helper: Ambil Teks Template Dinamis Lainnya
def get_rendered_template_text(cfg: dict, jenis: str, default_val: str) -> str:
    tmpl = cfg.get("templates", {}).get(jenis)
    ping_mentions = get_ping_roles_mentions(cfg.get("ping_roles", []))
    if isinstance(tmpl, dict):
        teks = tmpl.get("teks", default_val)
    elif isinstance(tmpl, str):
        teks = tmpl
    else:
        teks = default_val

    if ping_mentions and "{ping_roles_mentions}" in teks:
        teks = teks.replace("{ping_roles_mentions}", ping_mentions)
    elif ping_mentions and jenis in ["opening", "closing"] and "@&" not in teks:
        teks += f"\n\n{ping_mentions}"
    return teks

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
    embed.set_footer(text="Sistem Audit Absensi Otomatis")
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

        open_text = get_rendered_template_text(cfg, "opening", DEFAULT_TEMPLATES["opening"])
        absen_template = render_attendance_template(cfg)
        full_message = f"{open_text}\n\n━━━━━━━━━━━━━━━━━━\n{absen_template}"

        new_msg = await channel.send(full_message)
        await new_msg.pin()
        last_pinned_messages[guild_id] = new_msg.id
        return True
    except Exception as e:
        print(f"Error opening announcement: {e}")
        return False

async def execute_closing(channel: discord.TextChannel, cfg: dict):
    try:
        close_text = get_rendered_template_text(cfg, "closing", DEFAULT_TEMPLATES["closing"])
        await channel.send(close_text)
        return True
    except Exception as e:
        print(f"Error closing announcement: {e}")
        return False

# ==========================================
# ONBOARDING WIZARD UI
# ==========================================
class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="⚙️ Lihat Panduan Setup (/config)", style=discord.ButtonStyle.primary, custom_id="onboarding_guide")
    async def guide_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Hanya Owner atau Administrator yang dapat berinteraksi
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("❌ Hanya Server Owner atau Administrator yang dapat mengakses konfigurasi ini.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🛠️ Panduan Konfigurasi Awal Bot Absensi",
            description=(
                "Gunakan Slash Commands berikut untuk menyesuaikan sistem absensi server Anda:\n\n"
                "1. **Tentukan Role Wajib Absen:**\n`/config role_absen role:@Role aksi:tambah`\n\n"
                "2. **Tentukan Role Staf / Pengawas:**\n`/config role_staff role:@Role aksi:tambah`\n\n"
                "3. **Tentukan Role yang Di-ping di Form Absen:**\n`/config ping_role role:@Role aksi:tambah`\n\n"
                "4. **Atur Jam Buka / Tutup Otomatis (WIB):**\n`/config jadwal jam_buka:07:00 jam_tutup:22:00`\n\n"
                "5. **Periksa Konfigurasi Saat Ini:**\n`/config show`"
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="📋 Tampilkan Contoh Template", style=discord.ButtonStyle.secondary, custom_id="onboarding_preview")
    async def preview_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
            await interaction.response.send_message("❌ Hanya Administrator yang dapat melihat pratinjau ini.", ephemeral=True)
            return
        cfg = get_guild_config(interaction.guild.id)
        tmpl_preview = render_attendance_template(cfg)
        await interaction.response.send_message(f"**Pratinjau Format Absensi Saat Ini:**\n\n{tmpl_preview}", ephemeral=True)

# Helper Auto-Provisioning Channel saat bot masuk server baru
async def provision_channels_for_guild(guild: discord.Guild):
    # Cari channel yang sudah ada dengan kata kunci
    keywords = ["absen", "attendance", "rekap", "report"]
    found_absen = None
    found_rekap = None

    for ch in guild.text_channels:
        name_lower = ch.name.lower()
        if not found_absen and ("absen" in name_lower or "attendance" in name_lower) and "report" not in name_lower and "rekap" not in name_lower:
            found_absen = ch
        if not found_rekap and ("rekap" in name_lower or "report" in name_lower):
            found_rekap = ch

    # 1. Buat channel absensi jika belum ada
    if not found_absen:
        try:
            found_absen = await guild.create_text_channel(
                name="attendance",
                topic="Saluran presensi kehadiran resmi anggota"
            )
        except Exception as e:
            print(f"Gagal membuat channel attendance di {guild.name}: {e}")

    # 2. Buat channel rekap dengan izin terkunci jika belum ada
    if not found_rekap:
        try:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(send_messages=False, add_reactions=True, read_messages=True),
                guild.me: discord.PermissionOverwrite(send_messages=True, embed_links=True, manage_messages=True)
            }
            found_rekap = await guild.create_text_channel(
                name="attendance-report",
                topic="Laporan rekapitulasi kehadiran dinas mingguan (Read Only)",
                overwrites=overwrites
            )
        except Exception as e:
            print(f"Gagal membuat channel attendance-report di {guild.name}: {e}")

    # Simpan ke config database jika channel berhasil ditemukan/dibuat
    cfg = get_guild_config(guild.id)
    if found_absen:
        update_guild_config(guild.id, "absen_channel_id", found_absen.id)
    if found_rekap:
        update_guild_config(guild.id, "rekap_channel_id", found_rekap.id)

    # Kirim Onboarding Wizard ke channel absensi
    if found_absen:
        welcome_embed = discord.Embed(
            title="👋 Selamat Datang di Bot Otomasi Absensi!",
            description=(
                f"Halo! Bot telah otomatis menyiapkan infrastruktur saluran presensi di server **{guild.name}**:\n\n"
                f"• Saluran Absensi: {found_absen.mention}\n"
                f"• Saluran Laporan Rekap: {found_rekap.mention if found_rekap else '`(Belum dibuat)`'}\n\n"
                f"Nama channel di atas dapat diubah oleh Administrator kapan saja tanpa merusak sistem.\n"
                f"Klik tombol di bawah untuk melihat langkah konfigurasi awal."
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(pytz.UTC)
        )
        welcome_embed.set_footer(text="Hanya Server Owner / Administrator yang dapat mengonfigurasi")
        try:
            await found_absen.send(embed=welcome_embed, view=OnboardingView())
        except Exception as e:
            print(f"Gagal mengirim onboarding wizard di {guild.name}: {e}")

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
    await interaction.response.send_message("⏳ Membuka sesi absensi dan me-pin pengumuman...", ephemeral=True)
    success = await execute_opening(channel, cfg)
    if success:
        await interaction.followup.send("✅ Sesi absensi berhasil dibuka dan di-pin!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Terjadi kendala saat membuka sesi absensi.", ephemeral=True)

# 2. /tutup_absen
@bot.tree.command(name="tutup_absen", description="Tutup sesi absensi manual dan kirim pengumuman penutupan.")
async def slash_tutup_absen(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk menggunakan perintah ini.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    channel = interaction.guild.get_channel(cfg["absen_channel_id"]) or interaction.channel
    await interaction.response.send_message("⏳ Mengirim pengumuman penutupan absensi...", ephemeral=True)
    success = await execute_closing(channel, cfg)
    if success:
        await interaction.followup.send("✅ Sesi absensi telah ditutup.", ephemeral=True)
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
        title="📊 REKAPITULASI KEHADIRAN MINGGUAN",
        description=(
            f"**Periode Siklus:** `{start_date}` s/d `{end_date}`\n"
            f"**Total Anggota Wajib Absen:** {len(target_members)} Orang\n"
            f"**Standar Kehadiran:** Minimal 3x Hadir\n"
            f"**Hari Awal Siklus:** {cfg['start_day'].capitalize()}"
        ),
        color=discord.Color.blue(),
        timestamp=datetime.now(pytz.UTC)
    )

    disciplined_lines = [f"✅ **{m.mention}** (`{m.display_name}`): **{c}x** Hadir" for m, c in normal_list]
    chunk_text = "\n".join(disciplined_lines[:25]) if disciplined_lines else "Belum ada anggota yang mencapai 3x hadir."
    embed1.add_field(name=f"🟢 Anggota Memenuhi Standar (>= 3x) — [{len(normal_list)}]", value=chunk_text[:1024], inline=False)
    if len(disciplined_lines) > 25:
        embed1.add_field(name="🟢 Anggota Memenuhi Standar (Lanjutan)", value="\n".join(disciplined_lines[25:50])[:1024], inline=False)
    embed1.set_footer(text="Sistem Rekapitulasi Presensi • Halaman 1")
    pages.append(embed1)

    # Halaman 2: Personel Melanggar (<3x)
    embed2 = discord.Embed(
        title="⚠️ DAFTAR ANGGOTA KURANG DARI 3X HADIR",
        description=f"Anggota berikut belum memenuhi standar kehadiran pada periode `{start_date}` s/d `{end_date}`.",
        color=discord.Color.gold(),
        timestamp=datetime.now(pytz.UTC)
    )
    viol_lines = [f"⚠️ **{m.mention}** (`{m.display_name}`): Hanya **{c}x** Hadir" for m, c in violating_list]
    viol_chunk = "\n".join(viol_lines[:25]) if viol_lines else "Seluruh anggota memenuhi standar minimal!"
    embed2.add_field(name=f"🟡 Anggota Perlu Tindak Lanjut (< 3x) — [{len(violating_list)}]", value=viol_chunk[:1024], inline=False)
    if len(viol_lines) > 25:
        embed2.add_field(name="🟡 Anggota Perlu Tindak Lanjut (Lanjutan)", value="\n".join(viol_lines[25:50])[:1024], inline=False)
    embed2.set_footer(text="Sistem Rekapitulasi Presensi • Halaman 2")
    pages.append(embed2)

    view = RecapPaginationView(pages)
    await interaction.followup.send(embed=pages[0], view=view)

# 4. /tegur
@bot.tree.command(name="tegur", description="Kirim Embed Surat Teguran Kedisiplinan Resmi kepada anggota.")
@app_commands.describe(member="Anggota yang ditegur", pesan="Catatan pelanggaran kedisiplinan")
async def slash_tegur(interaction: discord.Interaction, member: discord.Member, pesan: str):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk menegur anggota.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    ping_mentions = get_ping_roles_mentions(cfg.get("ping_roles", []))

    embed = discord.Embed(
        title="⚠️ SURAT TEGURAN KEDISIPLINAN RESMI",
        description=(
            f"**Anggota Dituju:** {member.mention} (`{member.display_name}`)\n"
            f"**Staf Pengawas:** {interaction.user.mention}\n\n"
            f"**Catatan Pelanggaran:**\n```{pesan}```\n"
            f"⚠️ *Peringatan resmi ini dicatat ke dalam database kedisiplinan. "
            f"Harap segera meningkatkan kepatuhan presensi!*"
        ),
        color=discord.Color.gold(),
        timestamp=datetime.now(pytz.UTC)
    )
    embed.set_footer(text="Komando Pengawasan & Disiplin")

    await interaction.response.send_message(content=f"{member.mention} {ping_mentions}".strip(), embed=embed)
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

    ping_mentions = get_ping_roles_mentions(cfg.get("ping_roles", []))
    absen_ch = interaction.guild.get_channel(cfg["absen_channel_id"]) or interaction.channel

    await interaction.response.send_message(f"✅ Absensi {member.mention} untuk tanggal `{today_str}` berhasil dibatalkan.", ephemeral=True)
    await absen_ch.send(
        f"⚠️ Absen milik {member.mention} dibatalkan oleh Pengawas ({interaction.user.mention}) "
        f"karena: **{alasan}**. Silakan kirim ulang absensi yang benar.\n{ping_mentions}".strip()
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
        title="📖 PANDUAN LENGKAP SISTEM ABSENSI OTOMATIS",
        description="Berikut adalah daftar perintah Slash Commands (`/`) yang tersedia:",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="🛠️ Perintah Operasional",
        value=(
            "`/buka_absen` — Membuka sesi absen harian manual, auto-pin, dan kirim template.\n"
            "`/tutup_absen` — Menutup sesi absen manual dan mengirim pesan penutupan.\n"
            "`/rekap` — Menampilkan rekapitulasi kehadiran mingguan berhalaman (Embed pagination).\n"
            "`/tegur` — Mengirim surat teguran resmi kepada anggota yang melanggar.\n"
            "`/reject` — Membatalkan kehadiran member hari ini seketika."
        ),
        inline=False
    )
    embed.add_field(
        name="⚙️ Perintah Konfigurasi Server (`/config`)",
        value=(
            "`/config show` — Tampilkan seluruh pengaturan dinamis server aktif.\n"
            "`/config ping_role` — Tambah atau hapus role target mention baris ping template.\n"
            "`/config role_absen` — Tambah atau hapus role wajib absen.\n"
            "`/config role_staff` — Tambah atau hapus role staf pengawas (Admin/Mod).\n"
            "`/config jadwal` — Atur jam buka dan tutup absensi otomatis (WIB).\n"
            "`/config hari_awal` — Atur hari permulaan siklus 7 hari rekap mingguan.\n"
            "`/config channel` — Atur saluran absensi atau saluran rekap.\n"
            "`/config template` — Kustomisasi template teks dinamis bot.\n"
            "`/config reset` — Kembalikan pengaturan ke setelan awal default."
        ),
        inline=False
    )
    embed.set_footer(text="Sistem Otomasi Kehadiran & Kedisiplinan")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ==========================================
# INTERACTIVE ROLE SELECT VIEWS (MULTI-SELECT)
# ==========================================
class StaffRoleSelectView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Pilih 1 s/d 10 Role Staf Pengawas...",
        min_values=1,
        max_values=10
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        # Validasi keamanan: hanya pemanggil asli (Owner/Admin) yang dapat berinteraksi
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Anda tidak memiliki izin untuk memilih role ini.", ephemeral=True)
            return

        selected_roles = select.values
        selected_ids = [r.id for r in selected_roles]

        update_guild_config(interaction.guild.id, "staff_roles", selected_ids)

        roles_mentions = ", ".join([r.mention for r in selected_roles])
        embed = discord.Embed(
            title="✅ Role Staf Pengawas Berhasil Diperbarui",
            description=f"Daftar role staf pengawas aktif:\n{roles_mentions}",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

class AbsenRoleSelectView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id

    @discord.ui.select(
        cls=discord.ui.RoleSelect,
        placeholder="Pilih 1 s/d 10 Role Wajib Absen...",
        min_values=1,
        max_values=10
    )
    async def select_callback(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Anda tidak memiliki izin untuk memilih role ini.", ephemeral=True)
            return

        selected_roles = select.values
        selected_ids = [r.id for r in selected_roles]

        update_guild_config(interaction.guild.id, "wajib_absen_roles", selected_ids)

        roles_mentions = ", ".join([r.mention for r in selected_roles])
        embed = discord.Embed(
            title="✅ Role Wajib Absen Berhasil Diperbarui",
            description=f"Daftar role wajib absen aktif:\n{roles_mentions}",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)

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
    ping_roles_str = ", ".join([f"<@&{r}>" for r in cfg.get("ping_roles", [])]) or "Belum diatur"

    embed = discord.Embed(
        title=f"⚙️ Konfigurasi Server: {interaction.guild.name}",
        color=discord.Color.green(),
        timestamp=datetime.now(pytz.UTC)
    )
    embed.add_field(name="Saluran Absensi", value=absen_ch.mention if absen_ch else f"ID: {cfg['absen_channel_id']}", inline=True)
    embed.add_field(name="Saluran Rekap", value=rekap_ch.mention if rekap_ch else f"ID: {cfg['rekap_channel_id']}", inline=True)
    embed.add_field(name="Role Target Ping", value=ping_roles_str, inline=True)
    embed.add_field(name="Hari Awal Siklus", value=cfg["start_day"].capitalize(), inline=True)
    embed.add_field(name="Jadwal Otomatis (WIB)", value=f"Buka: `{cfg['open_time']}` | Tutup: `{cfg['close_time']}`", inline=True)
    embed.add_field(name="Role Wajib Absen", value=wajib_roles_str, inline=False)
    embed.add_field(name="Role Staf Pengawas", value=staff_roles_str, inline=False)
    embed.set_footer(text="Gunakan sub-command /config untuk mengubah pengaturan")

    await interaction.response.send_message(embed=embed, ephemeral=True)

@config_group.command(name="role_staff", description="Pilih role staf pengawas bot melalui menu interaktif (Multi-Select).")
async def config_role_staff(interaction: discord.Interaction):
    # Validasi Hak Akses: Server Owner atau Administrator
    if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
        await interaction.response.send_message("❌ Hanya Server Owner atau Administrator yang dapat mengatur role staf.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    current_staff = ", ".join([f"<@&{r}>" for r in cfg["staff_roles"]]) or "Belum diatur"

    embed = discord.Embed(
        title="👥 Pengaturan Role Staf Pengawas (Multi-Select)",
        description=(
            f"**Role Saat Ini:** {current_staff}\n\n"
            f"Silakan pilih **1 hingga 10 role** dari menu dropdown di bawah ini. "
            f"Seluruh role yang dipilih akan memiliki hak akses sebagai staf/moderator bot."
        ),
        color=discord.Color.blue()
    )
    view = StaffRoleSelectView(author_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@config_group.command(name="role_absen", description="Pilih role wajib absen melalui menu interaktif (Multi-Select).")
async def config_role_absen(interaction: discord.Interaction):
    # Validasi Hak Akses: Server Owner atau Administrator
    if not (interaction.user.guild_permissions.administrator or interaction.user.id == interaction.guild.owner_id):
        await interaction.response.send_message("❌ Hanya Server Owner atau Administrator yang dapat mengatur role wajib absen.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    current_wajib = ", ".join([f"<@&{r}>" for r in cfg["wajib_absen_roles"]]) or "Belum diatur"

    embed = discord.Embed(
        title="📋 Pengaturan Role Wajib Absen (Multi-Select)",
        description=(
            f"**Role Saat Ini:** {current_wajib}\n\n"
            f"Silakan pilih **1 hingga 10 role** dari menu dropdown di bawah ini. "
            f"Anggota dengan role tersebut wajib mengisi absensi harian dan masuk dalam rekapitulasi."
        ),
        color=discord.Color.blue()
    )
    view = AbsenRoleSelectView(author_id=interaction.user.id)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@config_group.command(name="ping_role", description="Tambah atau hapus role target yang di-mention pada baris Ping template absen.")
@app_commands.describe(role="Role target yang akan di-mention", aksi="Pilih tambah atau hapus")
async def config_ping_role(interaction: discord.Interaction, role: discord.Role, aksi: Literal["tambah", "hapus"]):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    ping_roles = cfg.get("ping_roles", [])
    if aksi == "tambah":
        if role.id not in ping_roles:
            ping_roles.append(role.id)
            update_guild_config(interaction.guild.id, "ping_roles", ping_roles)
            await interaction.response.send_message(f"✅ Role {role.mention} berhasil ditambahkan ke daftar target ping template.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} sudah ada di daftar target ping.", ephemeral=True)
    else:
        if role.id in ping_roles:
            ping_roles.remove(role.id)
            update_guild_config(interaction.guild.id, "ping_roles", ping_roles)
            await interaction.response.send_message(f"🗑️ Role {role.mention} berhasil dihapus dari daftar target ping.", ephemeral=True)
        else:
            await interaction.response.send_message(f"ℹ️ Role {role.mention} tidak ditemukan di daftar target ping.", ephemeral=True)

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
@app_commands.describe(
    jenis="Pilih template yang ingin diubah",
    teks="Teks template baru"
)
async def config_template(
    interaction: discord.Interaction,
    jenis: Literal["opening", "closing", "absen", "teguran", "peringatan"],
    teks: str
):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin.", ephemeral=True)
        return

    cfg = get_guild_config(interaction.guild.id)
    templates = cfg["templates"]

    templates[jenis] = teks
    update_guild_config(interaction.guild.id, "templates", templates)

    await interaction.response.send_message(
        f"✅ Template teks **{jenis}** berhasil diperbarui!",
        ephemeral=True
    )

@config_group.command(name="reset", description="Kembalikan seluruh pengaturan server ke setelan awal (default agnostik).")
async def config_reset(interaction: discord.Interaction):
    if not check_is_staff(interaction):
        await interaction.response.send_message("❌ Anda tidak memiliki izin untuk mereset pengaturan.", ephemeral=True)
        return

    gid_str = str(interaction.guild.id)
    cursor.execute("DELETE FROM guild_config WHERE guild_id = ?", (gid_str,))
    conn.commit()

    last_pinned_messages.pop(interaction.guild.id, None)

    # Re-inisialisasi konfigurasi default
    _ = get_guild_config(interaction.guild.id)

    embed = discord.Embed(
        title="🔄 Reset Konfigurasi Berhasil",
        description=(
            f"Seluruh pengaturan kustom untuk server **{interaction.guild.name}** "
            f"telah dihapus dan dikembalikan ke **setelan default universal**.\n\n"
            f"• **Jadwal Dinas:** `07:00` - `22:00` WIB\n"
            f"• **Hari Awal Rekap:** Senin\n"
            f"• **Template:** Format standar universal"
        ),
        color=discord.Color.green(),
        timestamp=datetime.now(pytz.UTC)
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
        except Exception as e:
            print(f"Error pada loop jadwal guild {guild.id}: {e}")

# ==========================================
# EVENTS (on_ready, on_guild_join, on_message, on_raw_reaction_add)
# ==========================================
@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap mengamankan absensi presensi!")
    try:
        synced = await bot.tree.sync()
        print(f"Berhasil mensinkronkan {len(synced)} Discord Slash Commands!")
    except Exception as e:
        print(f"Gagal mensinkronkan Slash Commands: {e}")

    # Daftarkan OnboardingView persistent
    bot.add_view(OnboardingView())

    if not check_dynamic_schedules.is_running():
        check_dynamic_schedules.start()

@bot.event
async def on_guild_join(guild: discord.Guild):
    print(f"Bot baru saja bergabung ke server: {guild.name} ({guild.id})")
    await provision_channels_for_guild(guild)

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
            normalized_content = content.replace("`", "")

            # Validasi 1: Wajib Melampirkan Foto / Screenshot
            if not message.attachments:
                await message.delete()
                await message.channel.send(
                    f"❌ {message.author.mention} Absen ditolak! Wajib menyertakan screenshot/foto in-game/bukti kehadiran.",
                    delete_after=15
                )
                await send_audit_log(
                    message.guild,
                    "❌ Absen Ditolak (Tanpa Foto)",
                    f"Absen dari {message.author.mention} otomatis ditolak karena tidak melampirkan foto/screenshot.",
                    color=discord.Color.red()
                )
                return

            # Validasi 2: Template Teks Absensi Wajib (Kata kunci inti: Nama & Status)
            required_keywords = ["nama:", "status:"]
            missing_keywords = [kw for kw in required_keywords if kw not in normalized_content.lower()]

            if missing_keywords:
                await message.delete()
                template_rendered = render_attendance_template(cfg)
                await message.channel.send(
                    f"⚠️ {message.author.mention} Format absen tidak sesuai!\n"
                    f"Wajib menggunakan template berikut secara presisi:\n{template_rendered}",
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
            new_template_hint = render_attendance_template(cfg)
            await message.channel.send(new_template_hint)

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
    ping_mentions = get_ping_roles_mentions(cfg.get("ping_roles", []))
    await channel.send(
        f"⚠️ Absen milik {target_user.mention} dibatalkan oleh Pengawas ({member.mention}) "
        f"karena foto/ketentuan tidak sesuai. Silakan kirim ulang absensi yang benar.\n{ping_mentions}".strip(),
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

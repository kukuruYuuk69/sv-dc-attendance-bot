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

# Template Teks Pembukaan (07:00 WIB)
OPENING_MESSAGE = """⏰ 【 SINYAL DINAS ON DUTY DIMULAI 】⏰

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

<@&1500083857591107744>"""

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

# ID Pinned Pembukaan Terakhir (untuk unpin harian)
last_pinned_opening_id = None

async def send_opening_announcement(channel):
    global last_pinned_opening_id
    try:
        # Bersihkan pin lama jika ada
        if last_pinned_opening_id:
            try:
                old_msg = await channel.fetch_message(last_pinned_opening_id)
                if old_msg.pinned:
                    await old_msg.unpin()
            except Exception as e:
                print(f"Gagal unpin pesan lama ({last_pinned_opening_id}): {e}")

        # Kirim pesan pembukaan baru dan pin
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
    channel_id = int(os.getenv("ABSEN_CHANNEL_ID", "0"))
    channel = bot.get_channel(channel_id)
    if channel:
        await send_opening_announcement(channel)

# Jadwal Penutupan Dinas (22:00 WIB / 15:00 UTC)
@tasks.loop(time=time(hour=15, minute=0, tzinfo=pytz.UTC))
async def schedule_closing():
    channel_id = int(os.getenv("ABSEN_CHANNEL_ID", "0"))
    channel = bot.get_channel(channel_id)
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

    ABSEN_CHANNEL_ID = int(os.getenv("ABSEN_CHANNEL_ID", "0"))
    ROLE_WAJIB_ABSEN_ID = int(os.getenv("ROLE_WAJIB_ABSEN_ID", "0"))

    if message.channel.id == ABSEN_CHANNEL_ID:
        now_wib = datetime.now(WIB)
        today_str = now_wib.strftime("%Y-%m-%d")
        is_wajib = any(role.id == ROLE_WAJIB_ABSEN_ID for role in message.author.roles)

        if is_wajib:
            content = message.content

            # Validasi 1: Wajib Melampirkan Foto / Screenshot
            if not message.attachments:
                await message.delete()
                await message.channel.send(
                    f"❌ {message.author.mention} Absen ditolak! Wajib menyertakan screenshot/foto in-game sesuai PRD.",
                    delete_after=15
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
                return

            # Validasi 3: Cek 1 Absen Sukses per Hari
            cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (str(message.author.id), today_str))
            if cursor.fetchone():
                await message.delete()
                await message.channel.send(
                    f"⚠️ {message.author.mention} Kamu sudah berhasil absen hari ini ({today_str}). Tidak diperbolehkan mengirim absen ganda!",
                    delete_after=15
                )
                return

            # Absen Diterima & Tercatat
            cursor.execute("INSERT INTO attendance (user_id, date) VALUES (?, ?)", (str(message.author.id), today_str))
            conn.commit()
            await message.add_reaction("✅")

    await bot.process_commands(message)

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

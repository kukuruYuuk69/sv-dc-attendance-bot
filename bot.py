import discord
from discord.ext import commands
import sqlite3
from datetime import datetime
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

@bot.event
async def on_ready():
    print(f"Bot {bot.user} siap mengamankan absensi sesuai PRD!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # ID Channel dan Role (Sesuaikan dengan server kamu nanti)
    ABSEN_CHANNEL_ID = int(os.getenv("ABSEN_CHANNEL_ID", "0"))
    ROLE_WAJIB_ABSEN_ID = int(os.getenv("ROLE_WAJIB_ABSEN_ID", "0"))

    if message.channel.id == ABSEN_CHANNEL_ID:
        now_wib = datetime.now(WIB)
        today_str = now_wib.strftime("%Y-%m-%d")
        is_wajib = any(role.id == ROLE_WAJIB_ABSEN_ID for role in message.author.roles)

        if is_wajib:
            # Validasi Wajib Foto
            if not message.attachments:
                await message.delete()
                await message.author.send("❌ Absen ditolak! Wajib menyertakan screenshot/foto in-game sesuai PRD.")
                return

            # Cek 1 Pesan per Hari
            cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (str(message.author.id), today_str))
            if cursor.fetchone():
                await message.delete()
                await message.author.send("⚠️ Kamu sudah berhasil absen hari ini. Tidak boleh mengirim absen ganda!")
                return

            # Catat Sukses
            cursor.execute("INSERT INTO attendance (user_id, date) VALUES (?, ?)", (str(message.author.id), today_str))
            conn.commit()
            await message.add_reaction("✅")

    await bot.process_commands(message)

token = os.getenv("DISCORD_BOT_TOKEN")
if token:
    bot.run(token)
else:
    print("Error: DISCORD_BOT_TOKEN tidak ditemukan di environment variables.")

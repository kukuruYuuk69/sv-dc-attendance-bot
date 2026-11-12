# Requirements: Discord Attendance & Automation Bot

## 1. Ikhtisar Sistem (Overview)
Proyek `sv-dc-attendance-bot` adalah bot presensi otomatis agnostik (universal) untuk Discord berbasis Python (`discord.py`) yang memanfaatkan SQLite lokal untuk penyimpanan data kehadiran dan konfigurasi per-server.

## 2. Kebutuhan Lingkungan & Dependensi (Prerequisites)
- **Python:** Versi 3.11 atau lebih baru
- **Git:** Versi 2.40 atau lebih baru
- **GitHub CLI (`gh`):** Untuk otomasi repository dan deployment
- **Discord Bot Application:**
  - Bot Token dari [Discord Developer Portal](https://discord.com/developers/applications)
  - Privileged Gateway Intents aktif:
    - `MESSAGE CONTENT INTENT`
    - `SERVER MEMBERS INTENT`

## 3. Daftar Pustaka Python (`requirements.txt`)
- `discord.py>=2.3.2`: Framework utama komunikasi Discord Gateway & Application Slash Commands (`tree.command`).
- `pytz>=2023.3`: Sinkronisasi zona waktu Indonesia (WIB / `Asia/Jakarta`).

## 4. Spesifikasi Arsitektur & Aturan Sistem

### 4.1 Desain Agnostik 100% (Universal)
- **Bebas Hardcode Role ID:** Tidak ada role ID bawaan instansi apa pun di dalam kode sumber.
- **Konfigurasi Mandiri Server:** Server baru dimulai dengan daftar `wajib_absen_roles`, `staff_roles`, dan `ping_roles` kosong (`[]`).
- **Template Bersih:** Jika belum ada role ping yang didaftarkan, baris `Ping:` pada template absensi harus kosong (`Ping: `) tanpa mention palsu atau broken tag `<@&...>`.

### 4.2 Struktur Database (`attendance.db`)
1. **`attendance`**
   - `user_id` (TEXT)
   - `date` (TEXT, format `YYYY-MM-DD`)
   - *Primary Key:* `(user_id, date)`

2. **`weekly_recap`**
   - `user_id` (TEXT)
   - `week_key` (TEXT, format `YYYY-MM-DD_to_YYYY-MM-DD`)
   - `attendance_count` (INTEGER)
   - `is_violation` (INTEGER: 0 atau 1)
   - `consecutive_violations` (INTEGER)
   - *Primary Key:* `(user_id, week_key)`

3. **`guild_config`**
   - `guild_id` (TEXT PRIMARY KEY)
   - `absen_channel_id` (TEXT)
   - `rekap_channel_id` (TEXT)
   - `wajib_absen_roles` (TEXT JSON List)
   - `staff_roles` (TEXT JSON List)
   - `open_time` (TEXT, default: `07:00`)
   - `close_time` (TEXT, default: `22:00`)
   - `start_day` (TEXT, default: `monday`)
   - `templates` (TEXT JSON Object)
   - `ping_roles` (TEXT JSON List)

### 4.3 Fitur Interaktif & Slash Commands (`/`)
- `/buka_absen`: Membuka sesi absensi manual & auto-pin template.
- `/tutup_absen`: Menutup sesi absensi manual.
- `/rekap`: Rekapitulasi mingguan berhalaman (Embed Pagination) dengan tombol ◀ / ▶.
- `/tegur`: Mengirimkan Embed Surat Teguran Kedisiplinan Resmi.
- `/reject`: Membatalkan kehadiran member hari ini seketika.
- `/help`: Panduan interaktif seluruh perintah bot.
- `/config show`: Menampilkan konfigurasi server aktif saat ini.
- `/config role_staff`: Interactive Multi-Select Role Menu untuk staf pengawas.
- `/config role_absen`: Interactive Multi-Select Role Menu untuk anggota wajib absen.
- `/config ping_role`: Menambah atau menghapus role target mention template.
- `/config jadwal`: Mengatur jam buka dan tutup absensi otomatis (WIB).
- `/config hari_awal`: Mengatur hari awal siklus 7 hari rekapitulasi.
- `/config channel`: Mengatur saluran absensi atau rekap.
- `/config template`: Kustomisasi template teks dinamis bot.
- `/config reset`: Mengembalikan seluruh pengaturan server ke setelan awal default.

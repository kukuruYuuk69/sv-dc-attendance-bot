# REQUIREMENTS DOCUMENT: MIGRASI RUNNER / HOSTING BOT KE GITHUB ACTIONS

## 1. Pendahuluan & Latar Belakang
Bot Discord Absensi Presensi (`sv-dc-attendance-bot`) saat ini berjalan pada lingkungan lokal pengembang. Untuk menjamin ketersediaan layanan (*high availability*), automasi CI/CD, dan operasional tanpa ketergantungan pada perangkat lokal yang menyala terus-menerus, sistem dipersiapkan untuk dapat dijalankan atau di-*deploy* melalui GitHub Actions.

Dokumen ini menganalisis arsitektur, kebutuhan sistem, manajemen rahasia (*secrets*), dan tantangan persistensi data saat menjalankan Discord bot berbasis Python & SQLite pada GitHub Actions runner.

---

## 2. Analisis Kebutuhan Sistem & Karakteristik Runner GitHub Actions

### 2.1 Sifat Lingkungan GitHub Actions Runner
- **Ephemeral Virtual Machine (VM)**: Lingkungan runner GitHub Actions (seperti `ubuntu-latest`) bersifat *stateless* dan *ephemeral*. Saat job atau workflow selesai, seluruh VM akan dihapus beserta seluruh sistem berkas lokalnya.
- **Batas Waktu Eksekusi (Execution Timeout)**:
  - Default maksimum eksekusi untuk satu job GitHub Actions adalah **6 jam (360 menit)**.
  - Untuk bot yang memerlukan koneksi WebSocket Gateway Discord 24/7, GitHub Actions perlu dievaluasi antara:
    1. Pola **Scheduled Re-trigger / Heartbeat Loop** (cron workflow yang me-restart job setiap interval tertentu sebelum batas 6 jam tercapai).
    2. Pola **Automated Continuous Deployment (CD)** ke platform PaaS/VPS eksternal (seperti Railway, Render, Fly.io, Oracle Cloud VM, atau Self-Hosted Runner).
    3. Pola **Self-Hosted Runner GitHub Actions** yang terhubung ke server/VPS pribadi pengguna.

### 2.2 Kebutuhan Utama
1. **Automasi Eksekusi**: File workflow YAML yang mendefinisikan langkah setup Python, dependensi, dan runtime execution.
2. **Kepatuhan CI**: Verifikasi sintaks kode (`python -m py_compile bot.py`) sebelum bot dijalankan untuk mencegah kegagalan runtime akibat kesalahan penulisan kode.
3. **Standarisasi Dependensi**: Menyediakan file `requirements.txt` yang berisi library spesifik (`discord.py`, `pytz`, `python-dotenv`) agar instalasi di VM runner konsisten dan cepat.

---

## 3. Standar Keamanan & Manajemen Kredensial (GitHub Repository Secrets)

### 3.1 Penghapusan Ketergantungan File `.env` Lokal
- File `.env` lokal tidak boleh di-commit ke repositori publik maupun privat.
- Seluruh variabel lingkungan wajib disuntikkan secara dinamis saat workflow dijalankan melalui `env:` block yang membaca GitHub Repository Secrets.

### 3.2 Daftar Kredensial & Secrets Wajib
| Nama Secret GitHub | Variabel Environment Bot | Keterangan | Tingkat Kerahasiaan |
| :--- | :--- | :--- | :--- |
| `DISCORD_TOKEN` | `DISCORD_BOT_TOKEN` | Token Bot Discord dari Discord Developer Portal | Kritis (Jangan bocor) |
| `LOG_CHANNEL_ID` | `LOG_CHANNEL_ID` | ID Text Channel untuk pengiriman log audit otomatis | Opsional / Publik Server |

### 3.3 Prinsip Keamanan Lingkungan Runner
- Runner tidak boleh menampilkan atau me-log nilai secret ke konsol (`echo` token dilarang keras).
- Token hanya diekspos ke proses Python runtime saat langkah eksekusi berlangsung.

---

## 4. Persistensi Database SQLite pada Lingkungan Runner

### 4.1 Tantangan Persistensi SQLite
Database `attendance.db` menyimpan 3 tabel krusial:
1. `attendance`: Riwayat absensi harian per user dan tanggal.
2. `weekly_recap`: Catatan pelanggaran dan akumulasi sanksi mingguan.
3. `guild_config`: Pengaturan dinamis per server (jadwal buka/tutup, channel, role staf/absen/ping, ambang batas).

Karena disk runner GitHub Actions bersifat *ephemeral*, file `attendance.db` akan hilang jika tidak ada mekanisme persistensi antar-eksekusi.

### 4.2 Strategi Solusi Persistensi
Untuk menjamin kesinambungan data pada GitHub Actions runner:
1. **Penyimpanan State via GitHub Branch Khusus / Auto-Commit (Database State Branch)**:
   - Sebelum runner dimatikan atau saat jadwal interval tertentu, workflow melakukan commit aman terhadap file `attendance.db` ke branch khusus (misal branch `db-data` atau branch terisolasi) menggunakan bot GitHub token (`GITHUB_TOKEN`).
   - Saat runner baru menyala, runner menarik (*fetch/checkout*) file `attendance.db` terakhir dari branch data tersebut sebelum menyalakan bot.
2. **Penyimpanan State via GitHub Actions Artifacts / Cache**:
   - Memanfaatkan aksi `actions/cache` atau `actions/upload-artifact` dan `actions/download-artifact` untuk memuat dan menyimpan file `attendance.db` antar siklus workflow.
3. **Alternatif Database Cloud (Jangka Panjang)**:
   - Mendukung integrasi masa depan ke database tersentralisasi berbasis cloud (seperti PostgreSQL / Supabase / Turso libSQL SQLite Cloud) yang tidak bergantung pada VM lokal runner.

---

## 5. Ringkasan Kriteria Keberhasilan (Acceptance Criteria)
1. Tersedianya file `requirements.txt` yang rapi dan tervalidasi.
2. Tersedianya file workflow GitHub Actions di `.github/workflows/` yang mampu menginstal dependensi dan memverifikasi integritas kode.
3. Penyusunan instruksi detail bagi admin/pemilik repo untuk mendaftarkan `DISCORD_TOKEN` di menu GitHub Repository Secrets.
4. Bot dapat membaca token dari Secrets tanpa mengalami *crash* atau error missing environment.

# REQUIREMENTS DOCUMENT: GRACEFUL SHUTDOWN & ZERO-COST GIT BACKUP

## 1. Pendahuluan
Dokumen ini mendefinisikan arsitektur ketahanan sesi (*session resilience*) dan strategi pencadangan database *zero-cost* untuk bot presensi Discord (`sv-dc-attendance-bot`). Solusi ini memungkinkan bot berjalan secara berkelanjutan di GitHub Actions tanpa biaya hosting eksternal (*free open-source infrastructure*), tanpa kartu kredit, serta menghindari konflik sesi ganda (*multiple session conflict*).

---

## 2. Analisis & Kebutuhan Inti

### 2.1 Graceful Auto-Exit (Estafet Runner GitHub Actions)
- **Masalah:** GitHub Actions membatasi waktu eksekusi job (maksimal 360 menit / 6 jam). Jika proses dihentikan secara paksa oleh sistem (*SIGKILL* / runner cancelation), koneksi database SQLite dapat mengalami kerusakan (*corrupted state* / *uncommitted transaction*), serta step pasca-eksekusi (*post-run steps*) berisiko tidak tereksekusi dengan sempurna.
- **Kebutuhan Sistem:**
  - Bot wajib dilengkapi dengan mekanisme *internal lifecycle timer* yang memantau durasi runtime sejak proses dinyalakan.
  - Setelah berjalan selama **295 menit (4 jam 55 menit)**, bot harus memulai prosedur penghentian anggun (*graceful shutdown*):
    1. Membatalkan / menyelesaikan background tasks (`tasks.loop`).
    2. Menutup transaksi dan koneksi SQLite (`conn.commit()`, `conn.close()`).
    3. Menutup koneksi Discord Gateway secara formal (`await bot.close()`).
    4. Mengakhiri proses dengan kode keluar sukses (`exit code 0`).
  - Hal ini menjamin runner menyelesaikan langkah eksekusi sebelum batas workflow 350 menit, sehingga step pencadangan data dapat dieksekusi secara aman dan mulus.

### 2.2 Zero-Cost Open Source Database Backup (Git Branch `db-backup`)
- **Masalah:** VM GitHub Actions bersifat *ephemeral*. Jika state database `attendance.db` tidak disimpan secara permanen, seluruh rekapitulasi presensi dan konfigurasi server akan hilang saat VM dimusnahkan.
- **Kebutuhan Sistem:**
  - Memanfaatkan fitur bawaan GitHub Actions menggunakan `GITHUB_TOKEN` default (tanpa perlu mendaftarkan Personal Access Token baru atau layanan pihak ketiga seperti S3, PostgreSQL cloud, atau Supabase).
  - Menyimpan file database `attendance.db` ke branch terisolasi bernama `db-backup` pada repositori yang sama (`kukuruYuuk69/sv-dc-attendance-bot`).
  - Alur Estafet Data:
    1. **Pre-Run (Restore):** Sebelum bot dijalankan, workflow mengecek keberadaan branch `db-backup`. Jika ditemukan, file `attendance.db` diunduh/di-checkout ke workspace runner. Jika belum ada, bot memulai dari skema awal.
    2. **Post-Run (Backup):** Setelah bot berhenti (baik karena mencapai 295 menit maupun terjadi interrupt), workflow secara otomatis melakukan commit dan push `attendance.db` terbaru ke branch `db-backup`.

### 2.3 Eliminasi Konflik Sesi (Matikan Host Lokal)
- **Masalah:** Discord Gateway membatasi koneksi bersamaan untuk bot yang menggunakan satu token identik tanpa sharding terkelola. Menjalankan bot di mesin lokal bersamaan dengan GitHub Actions runner akan memicu `Session Invalidated` (Opcode 9) dan disconnections berulang.
- **Kebutuhan Sistem:**
  - Seluruh instance bot lokal di mesin pengembang harus dihentikan secara permanen (`kill task`) sebelum workflow runner GitHub Actions dijalankan secara penuh.

---

## 3. Matriks Kriteria Penerimaan (Acceptance Criteria)
1. **Timer 295 Menit:** Bot berhenti secara otomatis dan bersih dengan log penutupan resmi pada menit ke-295.
2. **Koneksi Database Aman:** Tidak terjadi *database locked* atau *file corruption* saat auto-exit.
3. **Pencadangan Branch Otomatis:** Branch `db-backup` terbuat secara otomatis dan terbarui dengan snapshot `attendance.db` terbaru setiap kali job Actions selesai.
4. **Restorasi Mulus:** Data riwayat absensi, tabel rekap, dan `guild_config` yang tersimpan pada run sebelumnya tetap utuh saat runner baru menyala.
5. **Nirbiaya (Zero-Cost):** 100% menggunakan kuota free GitHub Actions dan storage Git bawaan tanpa kartu kredit atau layanan berbayar.

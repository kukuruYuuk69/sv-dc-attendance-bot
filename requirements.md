# REQUIREMENTS SPECIFICATION: DUPLICATE CHECK, DYNAMIC REFRESH & PENALTY THRESHOLD

## 1. Pendahuluan
Dokumen ini mendefinisikan kebutuhan sistem lanjutan untuk bot presensi `sv-dc-attendance-bot`, mencakup penegakan aturan anti-double absen harian, otomatisasi siklus template dinamis yang bersih di channel, perlakuan khusus bagi member baru melalui reset riwayat absensi, serta fleksibilitas pengaturan ambang batas sanksi/teguran mingguan.

---

## 2. Kebutuhan Sistem Lanjutan

### 2.1 Pencegahan Double Absen Harian (Anti-Duplicate Check)
- **Aturan Sistem:**
  - Satu user hanya diizinkan memiliki 1 kali status absensi sukses per hari (berdasarkan penanggalan WIB `YYYY-MM-DD`).
- **Logika Validasi:**
  - Sebelum memvalidasi format form atau lampiran gambar, bot memeriksa tabel `attendance` dengan query `WHERE user_id = ? AND date = ?`.
  - Jika data kehadiran user untuk hari tersebut sudah tercatat:
    1. Pesan baru user **otomatis dihapus seketika** (`message.delete()`).
    2. Bot mengirimkan pesan peringatan penolakan di channel absensi (men-tag user bersangkutan) yang menyatakan bahwa user sudah berhasil absen hari ini dan tidak diperbolehkan mengirim absen ganda.
    3. Pesan peringatan otomatis terhapus dalam waktu singkat (misal: 15 detik) untuk menjaga kebersihan saluran.

### 2.2 Siklus Pembaruan Template Dinamis (Clean Channel Lifecycle)
- **Skenario 1: Absen Sukses (`✅`):**
  - Ketika absen user valid dan dicatat ke database:
    1. Bot memberikan reaksi centang `✅` pada pesan user.
    2. Bot otomatis mengirimkan pesan template absensi baru di bawahnya agar template selalu berada di bagian terbawah aktivitas obrolan.
    3. *(Opsional/Pembersihan):* Bot dapat melacak dan menghapus template perantara sebelumnya agar tidak terjadi penumpukan template kosong di channel.
- **Skenario 2: Intervensi Reaksi Silang Staf (`❌`):**
  - Jika staf/pengawas memberikan reaksi `❌` pada pesan absen user:
    1. Data absensi user untuk hari tersebut dihapus dari database `attendance`.
    2. Pesan user yang disilang langsung dihapus seketika.
    3. Bot mengirimkan notifikasi penolakan (alasan foto/ketentuan tidak sesuai) yang hilang dalam 20 detik.
    4. Bot memastikan template absensi bersih tetap tersedia di posisi paling bawah saluran.

### 2.3 Reset Riwayat Absensi Member Baru (Refresh User Database)
- **Latar Belakang Masalah:**
  - Member baru yang baru bergabung di pertengahan minggu berisiko langsung terhitung melanggar (<3x hadir) atau terkena akumulasi alpha saat rekapitulasi akhir siklus dijalankan.
- **Kebutuhan Fitur:**
  - Tambahkan perintah staf (misal: `/config reset_user member:@User` atau `/reset_absen member:@User`):
    - Menghapus riwayat absensi dan catatan pelanggaran mingguan (`weekly_recap`) member tersebut.
    - Memberikan catatan "Fresh Start" sehingga member baru tidak langsung terkena penalti/teguran pada minggu pertama bergabung.
    - Mengirim konfirmasi tindakan staf dan mencatatnya ke audit log.

### 2.4 Konfigurasi Ambang Batas Teguran & Pelanggaran Beruntun (Configurable Thresholds)
- **Latar Belakang:**
  - Nilai standar minimal 3x absen per minggu dan ambang 2 minggu berturut-turut saat ini masih bersifat *hardcode*.
- **Kebutuhan Fitur:**
  - Tambahkan kolom konfigurasi pada tabel `guild_config`:
    - `min_attendance_weekly`: Jumlah minimal kehadiran per minggu (default: `3`).
    - `consecutive_threshold`: Jumlah minggu berturut-turut yang memicu Surat Teguran/Peringatan Keras (default: `2`).
  - Tambahkan sub-command `/config ambang_batas` (atau integrasi pada `/config`):
    - Parameter: `minimal_absen: int` (rentang 1–7) dan `minggu_beruntun: int` (rentang 1–4).
  - Sistem rekapitulasi mingguan dan evaluasi kedisiplinan wajib membaca nilai ambang batas ini secara dinamis dari database server.

---

## 3. Matriks Kebutuhan Fungsional

| ID Kebutuhan | Komponen | Deskripsi Singkat | Prioritas |
| :--- | :--- | :--- | :---: |
| **REQ-DUP-01** | `on_message` | Tolak & hapus pesan jika user sudah tercatat absen di hari yang sama. | Tinggi |
| **REQ-TMP-01** | `on_message` & `reaction` | Otomatis refresh template baru setelah sukses absen & setelah reaksi ❌. | Tinggi |
| **REQ-USR-01** | Slash Command | `/reset_user` untuk me-refresh riwayat kehadiran & rekap member baru. | Sedang |
| **REQ-CFG-01** | `guild_config` | Simpan `min_attendance_weekly` dan `consecutive_threshold` dinamis. | Tinggi |
| **REQ-CFG-02** | `/config ambang_batas` | Command staf untuk mengatur batas minimal kehadiran & minggu sanksi. | Sedang |

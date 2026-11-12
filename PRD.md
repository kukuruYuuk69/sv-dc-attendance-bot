# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis untuk mengelola absensi member ber-role wajib absen secara 100% gratis dengan validasi ketat, auto lock/unlock channel, auto-pin jadwal dinas/istirahat, sistem audit log, dan intervensi admin/moderator.

## 2. Aturan & Fitur Utama

### 2.1 Error Handling & Saluran Notifikasi
- **Peringatan Langsung di Channel:** Jika absen member ditolak (tidak ada screenshot/foto in-game, format tidak sesuai, atau sudah absen di hari yang sama), bot mengirimkan pesan peringatan langsung ke saluran (`channel`) absensi tempat member tersebut mengirim pesan, bukan via Direct Message (DM).

### 2.2 Format Template Absensi Wajib (Member)
Setiap pesan absen yang dikirim oleh member wajib melampirkan screenshot/foto in-game serta mematuhi format teks berikut secara presisi:
```text
Nama: 
Pangkat: 
Job: 
Divisi: 
Status: Hadir
Ping: <@&1500812071024197682>
```

### 2.3 Siklus Kirim Template Otomatis
- Setiap kali member berhasil absen dan disetujui (diberi reaksi `✅`), bot otomatis mengirimkan template absensi baru di channel agar selalu berada di bawah pesan terbaru.

### 2.4 Intervensi Admin & Moderator (Pembatalan Absen)
- **Reaksi Intervensi (`❌`):** Jika Admin/Moderator memberikan reaksi `❌` pada pesan absen member di channel absen:
  1. Bot otomatis menghapus data kehadiran member tersebut dari database SQLite (`attendance.db`).
  2. Bot mengirimkan pemberitahuan di channel: *"⚠️ Absen milik @Member dibatalkan oleh Moderator karena foto tidak sesuai ketentuan. Silakan kirim ulang."* (disertai tag role pengawas).
  3. Mengirimkan catatan audit ke channel log.
- **Perintah Manual (`!reject @member [alasan]`):** Admin/Moderator dapat membatalkan absensi seorang member secara manual disertai alasan penolakan.

### 2.5 Sistem Audit Log
- Setiap peristiwa absensi disetujui, ditolak (otomatis/manual), atau dibatalkan oleh moderator akan dicatat ke channel audit log (`LOG_CHANNEL_ID`).

### 2.6 Pesan Pembukaan Absen (Jam 07:00 WIB / 00:00 UTC)
Setiap pukul 07:00 WIB:
- Channel `#absen` dibuka (unlock izin kirim pesan bagi role wajib absen).
- Bot menghapus pin pengumuman pembukaan hari sebelumnya.
- Bot mengirimkan pesan pengumuman pembukaan dinas beserta template absensi ke channel `#absen` dan me-pin pesan tersebut.

### 2.7 Pesan Penutupan Absen (Jam 22:00 WIB / 15:00 UTC)
Setiap pukul 22:00 WIB:
- Channel `#absen` dikunci (lock izin kirim pesan bagi role wajib absen).
- Bot mengirimkan pesan penutupan dinas ke channel `#absen`.

### 2.8 Rekap Mingguan
- Setiap hari Minggu pukul 22:00 WIB, bot merangkum data kehadiran dari SQLite dan mengirimkan rekap ke channel `#rekap-absen`.

# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis untuk mengelola absensi member ber-role wajib absen secara 100% gratis dengan validasi ketat, auto lock/unlock channel, dan rekapitulasi mingguan.

## 2. Aturan & Fitur Utama
- **Auto Lock/Unlock:** Channel `#absen` dibuka jam 07:00 WIB dan dikunci jam 22:00 WIB.
- **Validasi Wajib Foto:** Pesan wajib melampirkan gambar/screenshot in-game. Jika tidak ada, pesan dihapus dan bot mengirim DM peringatan.
- **Batasan 1 Pesan/Hari:** Member hanya bisa sukses absen 1 kali per hari. Jika salah format (pesan dihapus), member diizinkan mengirim ulang pada hari yang sama.
- **Rekap Mingguan:** Setiap hari Minggu pukul 22:00 WIB, bot merangkum data kehadiran dari SQLite dan mengirimkannya ke channel `#rekap-absen`.

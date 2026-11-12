# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis untuk mengelola absensi member ber-role wajib absen secara 100% gratis dengan validasi ketat, auto lock/unlock channel, auto-pin jadwal dinas/istirahat, sistem audit log, intervensi admin/moderator, serta sistem rekapitulasi mingguan otomatis & tracking pelanggaran beruntun.

## 2. Aturan & Fitur Utama

### 2.1 Error Handling & Saluran Notifikasi
- **Peringatan Langsung di Channel:** Jika absen member ditolak (tanpa screenshot/foto in-game, format tidak sesuai, atau sudah absen di hari yang sama), bot mengirimkan pesan peringatan langsung ke saluran absensi (men-tag member) dan pesan terhapus otomatis setelah batas waktu.
- **Hapus Pesan saat Di-react Silang (`❌`):** Jika Admin/Moderator memberikan reaksi `❌` pada pesan absen member, bot menghapus catatan di database dan seketika menghapus pesan absen terkait.

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

### 2.4 Sistem Rekapitulasi Mingguan & Standar Disiplin
- **Siklus Minggu:** Dihitung dari hari **Senin** (00:00 WIB) hingga hari **Minggu** pukul 22:00 WIB.
- **Waktu Rekap Otomatis:** Setiap hari **Minggu pukul 22:00 WIB** (15:00 UTC), bot otomatis merekap kehadiran member ber-role wajib absen dan mengirimkannya ke channel rekap ID `1570460912572178443`.
- **Standar Minimal Kehadiran:** Minimal **3 kali absen per minggu**.
- **Peringatan Pelanggaran (<3x):** Jika member absen kurang dari 3 kali, bot menandai status PELANGGARAN dan men-tag role Admin dan Moderator di channel rekap.
- **Tracking Pelanggaran Beruntun (Consecutive Violations):** Bot mencatat pelanggaran per minggu ke database. Jika member melanggar 2 minggu berturut-turut, bot mengirimkan peringatan darurat/khusus untuk penalti tegas.

### 2.5 Perintah Admin & Moderator
- `!rekap`: Memicu kalkulasi dan penampilan rekapitulasi kehadiran minggu berjalan secara on-demand.
- `!tegur @member [pesan]`: Mengirimkan teguran kedisiplinan resmi kepada personel di channel dan mencatatnya ke audit log.
- `!override_absen @member [tambah/kurang] [YYYY-MM-DD]`: Menyesuaikan catatan kehadiran member secara manual.
- `!reject @member [alasan]`: Membatalkan kehadiran member pada hari ini secara instan.
- `!buka_absen` & `!tutup_absen`: Mengirim pengumuman dinas/istirahat secara manual.

### 2.6 Sistem Audit Log
- Setiap absensi masuk, penolakan, intervensi reaksi silang, dan teguran tercatat rapi ke channel log (`LOG_CHANNEL_ID`).

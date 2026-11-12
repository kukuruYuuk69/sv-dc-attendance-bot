# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis untuk mengelola absensi member ber-role wajib absen secara 100% gratis dengan validasi ketat, auto lock/unlock channel, auto-pin jadwal dinas/istirahat, dan rekapitulasi mingguan.

## 2. Aturan & Fitur Utama

### 2.1 Error Handling & Saluran Notifikasi
- **Peringatan Langsung di Channel:** Jika absen member ditolak (tidak ada screenshot/foto in-game, format tidak sesuai, atau sudah absen di hari yang sama), pesan pesan ditolak/dihapus dan bot **wajib mengirimkan pesan peringatan langsung ke saluran (`channel`) absensi** (men-tag member terkait), **bukan via Direct Message (DM)**.

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

### 2.3 Batasan Absen
- **1 Absen Sukses per Hari:** Member hanya dapat sukses absen 1 kali per hari (berdasarkan zona waktu WIB / Asia/Jakarta).
- **Kesempatan Kirim Ulang:** Jika pesan dihapus karena format tidak sesuai atau tidak menyertakan foto, member diizinkan mengirim ulang absen yang benar pada hari yang sama.

### 2.4 Pesan Pembukaan Absen (Jam 07:00 WIB / 00:00 UTC)
Setiap pukul 07:00 WIB:
- Channel `#absen` dibuka (unlock izin kirim pesan bagi role wajib absen).
- Bot menghapus pin pengumuman pembukaan hari sebelumnya (opsional/pembersihan otomatis).
- Bot mengirimkan pesan pengumuman pembukaan dinas ke channel `#absen` dan langsung melakukan **Pin** (`.pin()`):

```text
⏰ 【 SINYAL DINAS ON DUTY DIMULAI 】⏰

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

<@&1500083857591107744>

━━━━━━━━━━━━━━━━━━
📋 **TEMPLATE ABSENSI:**
```text
Nama: 
Pangkat: 
Job: 
Divisi: 
Status: Hadir
Ping: <@&1500812071024197682>
```
*(Wajib menyertakan screenshot/foto in-game)*
```

### 2.5 Pesan Penutupan Absen (Jam 22:00 WIB / 15:00 UTC)
Setiap pukul 22:00 WIB:
- Channel `#absen` dikunci (lock izin kirim pesan bagi role wajib absen).
- Bot mengirimkan pesan penutupan dinas ke channel `#absen`:

```text
# 【 WAKTU ISTIRAHAT TELAH TIBA 】

Seluruh personel Paspampres ANS dipersilakan mengakhiri aktivitas dan memasuki waktu istirahat.

```- Gunakan waktu malam untuk memulihkan energi
- Hindari aktivitas yang mengganggu kesiapan esok hari
- Jaga sikap dan ketertiban di lingkungan masing-masing
- Pastikan kesiapan untuk pelaksanaan dinas berikutnya```
━━━━━━━━━━━━━━━━━━
💤 Istirahat yang cukup adalah bagian dari kesiapan tempur.
━━━━━━━━━━━━━━━━━━
<@&1500083857591107744>
```

### 2.6 Rekap Mingguan
- Setiap hari Minggu pukul 22:00 WIB, bot merangkum data kehadiran dari SQLite dan mengirimkan rekap ke channel `#rekap-absen`.

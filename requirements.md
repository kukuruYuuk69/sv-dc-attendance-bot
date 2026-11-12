# REQUIREMENTS SPECIFICATION: ATTENDANCE & AUTOMATION BOT

## 1. Pendahuluan
Dokumen ini mendefinisikan kebutuhan perubahan fungsional dan teknis pada repositori `sv-dc-attendance-bot` sebelum dilakukannya modifikasi pada kode program `bot.py`. Fokus utama pembaruan ini meliputi penghapusan fitur *auto-pin*, otomasi penjadwalan dinamis berbasis server, dan standardisasi interaktivitas tampilan pengguna (*user mention*).

---

## 2. Kebutuhan Perubahan Sistem

### 2.1 Evaluasi & Penghapusan Fitur Auto-Pin Template
- **Kondisi Saat Ini:**
  - Bot secara otomatis menyematkan (*pin*) pesan pengumuman pembukaan dinas (`await new_msg.pin()`) dan mencoba melepas sematan (*unpin*) pesan hari sebelumnya.
- **Masalah & Pertimbangan:**
  - Discord membatasi jumlah pesan yang dapat di-pin dalam satu channel (maksimal 50 pesan).
  - Aktivitas *pin/unpin* harian menghasilkan notifikasi sistem Discord berulang dan membebani rate limit channel.
  - Template absensi sudah selalu dikirimkan ulang secara otomatis tepat di bawah pesan absensi yang baru masuk, sehingga pinning pesan pembukaan tidak lagi esensial.
- **Kebutuhan Baru:**
  - **Hapus total fitur *auto-pin* dan *unpin* pada pesan pembukaan dinas.**
  - Pengumuman pembukaan dinas cukup dikirimkan sebagai pesan teks biasa ke saluran absensi tanpa memanggil fungsi `.pin()`.

### 2.2 Penjadwalan Dinamis Rekapitulasi Mingguan (`tasks.loop`)
- **Kondisi Saat Ini:**
  - Pengecekan rekapitulasi otomatis masih memiliki sisa logika hardcode yang mengecek hari Minggu (`now_wib.weekday() == 6`).
- **Masalah & Pertimbangan:**
  - Setiap server dapat memiliki siklus dinas 7 hari yang berbeda-beda melalui perintah `/config hari_awal` (misalnya: dimulai hari Rabu dan berakhir hari Selasa malam).
- **Kebutuhan Baru:**
  - Sistem background scheduler (`tasks.loop`) wajib menghitung hari penutupan siklus secara dinamis berdasarkan nilai `start_day` yang tersimpan di `guild_config`.
  - Hari penutupan mingguan dihitung tepat **6 hari setelah `start_day`** pada jam `close_time` (WIB) server tersebut.
  - Rekapitulasi mingguan otomatis hanya terpicu jika hari saat ini dan jam saat ini cocok dengan siklus akhir guild terkait.

### 2.3 Standarisasi Format Mention & Tampilan Profil Interaktif
- **Kondisi Saat Ini:**
  - Sebagian pencetakan nama masih menggunakan kombinasi string manual seperti `m.name`, `m.display_name`, atau tag statis.
- **Masalah & Pertimbangan:**
  - Pengguna di server Discord menginginkan tampilan nama sesuai *Server Nickname* / *Display Name* yang dapat diklik (*clickable mention*) untuk membuka profil server secara interaktif.
- **Kebutuhan Baru:**
  - Semua pesan laporan (rekapitulasi mingguan, surat teguran `/tegur`, notifikasi penolakan `/reject`, dan audit log) wajib menggunakan format objek Discord Member yang merender mention interaktif:
    - Di dalam chat: Menggunakan `member.mention` (menampilkan `@NamaServer` yang dapat diklik).
    - Di dalam Embed / text description: Menggunakan kombinasi `${member.mention} (${member.display_name})`.

---

## 3. Matriks Kebutuhan Fungsional

| ID Kebutuhan | Komponen | Deskripsi Singkat | Prioritas |
| :--- | :--- | :--- | :---: |
| **REQ-PIN-01** | `execute_opening` | Hapus aksi `.pin()` dan pembersihan pin lama. | Tinggi |
| **REQ-SCH-01** | `check_dynamic_schedules` | Kalkulasi hari akhir siklus mingguan dinamis `(start_idx + 6) % 7`. | Tinggi |
| **REQ-SCH-02** | `check_dynamic_schedules` | Trigger otomatis rekap mingguan pada jam `close_time` hari akhir siklus. | Tinggi |
| **REQ-UI-01** | `slash_rekap` | Gunakan `member.mention` dan `member.display_name` interaktif pada Embed. | Sedang |
| **REQ-UI-02** | `slash_tegur` & `reject` | Pastikan tag staf dan target member interaktif dan dapat diklik. | Sedang |

# REQUIREMENTS DOCUMENT: AUTO-LOCK & UNLOCK SALURAN ABSENSI

## 1. Pendahuluan
Saluran absensi (`absen_channel_id`) merupakan kanal resmi presensi kedisiplinan anggota. Saat ini, ketika sesi absensi ditutup melalui jadwal otomatis (`close_time`) atau slash command `/tutup_absen`, bot hanya mengirimkan pesan pengumuman penutupan tanpa mengubah izin kirim pesan. Hal ini membuka celah bagi anggota untuk tetap mengirim pesan, presensi terlambat, atau spam di luar jam operasional dinas.

Dokumen ini menetapkan kebutuhan sistem untuk menerapkan mekanisme **Auto-Lock & Unlock Saluran Absensi** berbasis modifikasi hak akses saluran Discord (*Channel Permission Overwrite*).

---

## 2. Analisis & Kebutuhan Inti

### 2.1 Penguncian Otomatis Saluran Absensi (Auto-Lock)
- **Kondisi Pemicu:**
  1. Trigger jadwal otomatis penutupan dinas (`close_time` pada loop per menit).
  2. Eksekusi manual slash command `/tutup_absen` oleh staf pengawas atau administrator.
- **Tindakan Sistem:**
  - Mengubah izin saluran absensi untuk role default server (`@everyone` / `guild.default_role`):
    - `send_messages = False`
  - Memastikan bot dan staf pengawas tetap mempertahankan izin akses dan kelola saluran (`send_messages = True`).
  - Mengirimkan pengumuman penutupan absensi yang memberi tahu seluruh anggota bahwa sesi telah berakhir dan saluran telah dikunci.

### 2.2 Pembukaan Otomatis Saluran Absensi (Auto-Unlock)
- **Kondisi Pemicu:**
  1. Trigger jadwal otomatis pembukaan dinas (`open_time` pada loop per menit).
  2. Eksekusi manual slash command `/buka_absen` oleh staf pengawas atau administrator.
- **Tindakan Sistem:**
  - Mengembalikan izin kirim pesan saluran absensi untuk role `@everyone`:
    - `send_messages = True` (atau `None` jika mengikuti warisan kategori, direkomendasikan eksplisit `True` untuk menjamin anggota dapat absen).
  - Mengirimkan pengumuman pembukaan dinas beserta template formulir absensi baru di posisi bawah.

### 2.3 Pencegahan Pesan di Luar Jam Operasional
- Dengan terkuncinya saluran secara hak akses Discord:
  - Input teks pengguna di Discord client langsung dinonaktifkan (kotak pesan bertuliskan *"You do not have permission to send messages in this channel"*).
  - Mengurangi beban komputasi bot dan log audit karena tidak perlu menghapus pesan ilegal yang masuk saat sesi tutup.
  - Menghilangkan friksi perdebatan waktu presensi karena sistem saluran terkunci secara objektif dan tersinkronisasi dengan waktu WIB.

---

## 3. Matriks Kriteria Penerimaan (Acceptance Criteria)
1. **Eksekusi Penutupan:** Saat `/tutup_absen` atau `close_time` tercapai, role `@everyone` tidak lagi dapat mengirim pesan ke saluran absensi.
2. **Eksekusi Pembukaan:** Saat `/buka_absen` atau `open_time` tercapai, role `@everyone` kembali dapat mengirim pesan ke saluran absensi.
3. **Ketahanan Izin Staf & Bot:** Bot dan role staf tidak kehilangan akses mengelola pesan di saluran absensi meskipun saluran sedang terkunci.
4. **Penanganan Error Izin:** Jika bot tidak memiliki izin `Manage Channels` (`manage_permissions`), sistem menangani error secara aman melalui log audit tanpa memicu *bot crash*.

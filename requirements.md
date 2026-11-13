# REQUIREMENTS DOCUMENT: PERBAIKAN BUG AUTO-LOCK SALURAN ABSENSI

## 1. Latar Belakang & Analisis Akar Masalah (Root Cause)
Pada implementasi sebelumnya, ditemukan anomali di mana anggota dengan role `wajib_absen_roles` masih dapat mengirimkan pesan di saluran absensi meskipun status sesi telah ditutup (`is_open = False`).

Setelah dilakukan penelusuran arsitektur kode:
1. **Ketidaksesuaian Tipe Data (`str` vs `int`):** Nilai `r_id` yang tersimpan atau dibaca dari JSON SQLite terkadang berformat string (misalnya `"123456789"`), sedangkan `guild.get_role(role_id)` di discord.py mengharuskan tipe data integer (`int`). Jika tidak di-cast eksplisit ke `int(r_id)`, `guild.get_role()` menghasilkan `None`, sehingga iterasi `set_permissions` dilewati diam-diam tanpa menerapkan pembatasan.
2. **Izin Parsial & Celah Thread:** Discord memiliki izin turunan seperti `send_messages_in_threads` dan `create_public_threads`. Jika hanya `send_messages` yang diubah, anggota tertentu berpotensi masih dapat memicu pesan atau reaksi di saluran.
3. **Ketidaksinkronan saat Update Role (`/config role_absen`):** Ketika admin memperbarui daftar role wajib absen melalui command `/config role_absen`, permission saluran absensi saat itu tidak langsung diperbarui, sehingga role baru yang baru didaftarkan belum mendapatkan aturan pembatasan yang sesuai.
4. **Kurangnya Logging Kegagalan Izin (`discord.Forbidden`):** Jika bot kekurangan izin `Manage Permissions` atau `Manage Channels`, penanganan exception hanya mencetak pesan umum tanpa memberikan rincian audit log yang jelas.

---

## 2. Kebutuhan Sistem & Spesifikasi Perbaikan

### 2.1 Konversi Tipe Data Mutlak (`int(role_id)`)
- Seluruh iterasi role ID dari konfigurasi `guild_config` (`wajib_absen_roles`, `staff_roles`, `ping_roles`) wajib dikonversi secara aman melalui `int(role_id)`.
- Jika konversi gagal atau role tidak ditemukan di server, bot harus mencatat peringatan dan melanjutkan ke role berikutnya tanpa menggagalkan fungsi utama.

### 2.2 Penegakan Overwrite Eksplisit & Ketat (*Strict Permission Overwrite*)
Saat sesi ditutup (`is_open = False`):
- **`@everyone`**:
  - `view_channel = False`
  - `send_messages = False`
  - `send_messages_in_threads = False`
  - `create_public_threads = False`
  - `create_private_threads = False`
  - `add_reactions = False`
- **Setiap Role di `wajib_absen_roles`**:
  - `view_channel = True`
  - `send_messages = False` *(Eksplisit terkunci)*
  - `send_messages_in_threads = False`
  - `create_public_threads = False`
  - `create_private_threads = False`
  - `add_reactions = False` (atau disesuaikan jika reaksi diizinkan)
- **`Bot (guild.me)`**:
  - `view_channel = True`, `send_messages = True`, `manage_messages = True`, `manage_permissions = True`.
- **`staff_roles`**:
  - Tetap `view_channel = True`, `send_messages = True` untuk kebutuhan kontrol dan pengawasan.

Saat sesi dibuka (`is_open = True`):
- **Setiap Role di `wajib_absen_roles`**:
  - `view_channel = True`
  - `send_messages = True`
  - `attach_files = True`
  - `embed_links = True`
  - `read_message_history = True`

### 2.3 Sinkronisasi Real-Time saat Perubahan Konfigurasi Role
- Ketika sub-command `/config role_absen` atau `/config role_staff` dieksekusi, bot harus segera memanggil `update_attendance_channel_permissions` agar saluran absensi langsung disesuaikan dengan daftar role baru sesuai status buka/tutup saat itu.

### 2.4 Error Handling & Audit Log Khusus `discord.Forbidden`
- Tambahkan logging spesifik yang mendeteksi apakah kegagalan pengubahan izin disebabkan oleh hierarki role Discord (role bot berada di bawah role yang hendak diatur) atau kekurangan permission `Manage Permissions`.

---

## 3. Matriks Kriteria Penerimaan (Acceptance Criteria)
1. **Zero Message Leak:** Anggota dengan role wajib absen (non-admin) tidak dapat mengetik pesan, thread, maupun reaksi saat bot dalam mode sesi tutup.
2. **Robust Role Lookup:** Tidak ada role yang terlewat dalam iterasi akibat inkonsistensi tipe string/integer.
3. **Instant Role Sync:** Penambahan atau pengurangan role via `/config role_absen` langsung merefleksikan izin saluran seketika.
4. **Informative Diagnostics:** Error perizinan tercatat jelas di konsol dan audit log.

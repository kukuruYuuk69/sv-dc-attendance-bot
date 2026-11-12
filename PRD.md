# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis multi-server berbasis Discord Slash Commands (`/`) dan database konfigurasi dinamis (`attendance.db`) untuk mengelola absensi member wajib absen dengan validasi ketat, auto lock/unlock channel, auto-pin pengumuman dinas, layout template standar, konfigurasi ping role dinamis & terintegrasi, fitur reset konfigurasi, penolakan otomatis/manual, sistem audit log, serta rekapitulasi mingguan berhalaman (Embed pagination) dan peringatan pelanggaran beruntun.

## 2. Fitur & Arsitektur Utama

### 2.1 Database Konfigurasi Dinamis (`guild_config`)
Setiap server (guild) memiliki pengaturan tersendiri yang tersimpan di SQLite:
- `guild_id` (TEXT PRIMARY KEY)
- `absen_channel_id` (TEXT)
- `rekap_channel_id` (TEXT)
- `wajib_absen_roles` (TEXT - JSON list ID role wajib absen)
- `staff_roles` (TEXT - JSON list ID role Admin & Moderator)
- `ping_role_id` (TEXT - ID role yang otomatis di-ping pada baris `Ping:` di template absensi)
- `open_time` (TEXT - format 'HH:MM', default '07:00')
- `close_time` (TEXT - format 'HH:MM', default '22:00')
- `start_day` (TEXT - default 'monday', opsi: senin s/d minggu)
- `templates` (TEXT - JSON object menyimpan template dinamis: opening, closing, absen, teguran, peringatan)

### 2.2 Struktur Layout Template Absensi Standar
Template absensi yang dikirim oleh bot memiliki tata letak 3 bagian yang konsisten:
1. **Header:** `📋 TEMPLATE ABSENSI:` (di luar code block).
2. **Kotak Code Block (`` ```text ``):**
   ```text
   Nama: 
   Pangkat: 
   Job: 
   Divisi: 
   Status: Hadir
   Ping: <@&ROLE_ID>
   ```
3. **Footer:** `*(Wajib menyertakan screenshot/foto in-game)*` di bagian paling bawah.

### 2.3 Command Group Pengaturan Server (`/config`)
- `/config show`: Menampilkan ringkasan konfigurasi server aktif dalam bentuk Embed (`ephemeral=True`).
- `/config template` (`jenis: opening/closing/absen/teguran/peringatan`, `teks`, `role_ping` [opsional]): Kustomisasi teks template dan role yang di-mention secara terstruktur.
- `/config reset`: Mengembalikan pengaturan server ke setelan awal (*default* PASPAMPRES) dengan menghapus data kustom di database (`ephemeral=True`).
- `/config ping_role` (`role: discord.Role`): Mengatur role yang otomatis di-mention pada baris `Ping:` di template absensi.
- `/config role_absen` (`role`, `aksi: tambah/hapus`): Atur role wajib absen.
- `/config role_staff` (`role`, `aksi: tambah/hapus`): Atur role staf pengawas (Admin/Moderator).
- `/config jadwal` (`jam_buka`, `jam_tutup`): Atur jam buka dan tutup absensi dinas (WIB).
- `/config hari_awal` (`hari`): Atur hari permulaan siklus 7 hari rekapitulasi mingguan.
- `/config channel` (`tipe: absensi/rekap`, `channel`): Atur saluran absensi atau rekap.

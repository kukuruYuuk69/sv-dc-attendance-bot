# PRD: Discord Attendance & Automation Bot (SV DC)

## 1. Tujuan Proyek
Membuat bot Discord otomatis multi-server berbasis Discord Slash Commands (`/`) dan database konfigurasi dinamis (`attendance.db`) untuk mengelola absensi member wajib absen dengan validasi ketat, auto lock/unlock channel, auto-pin pengumuman dinas, penolakan otomatis/manual, sistem audit log, serta rekapitulasi mingguan berhalaman (Embed pagination) dan peringatan pelanggaran beruntun.

## 2. Fitur & Arsitektur Utama

### 2.1 Database Konfigurasi Dinamis (`guild_config`)
Setiap server (guild) memiliki pengaturan tersendiri yang tersimpan di SQLite:
- `guild_id` (TEXT PRIMARY KEY)
- `absen_channel_id` (TEXT)
- `rekap_channel_id` (TEXT)
- `wajib_absen_roles` (TEXT - JSON list ID role wajib absen)
- `staff_roles` (TEXT - JSON list ID role Admin & Moderator)
- `open_time` (TEXT - format 'HH:MM', default '07:00')
- `close_time` (TEXT - format 'HH:MM', default '22:00')
- `start_day` (TEXT - default 'monday', opsi: senin, selasa, rabu, kamis, jumat, sabtu, minggu)
- `templates` (TEXT - JSON object menyimpan template dinamis: opening, closing, absen, teguran, peringatan)

### 2.2 Migrasi Penuh ke Discord Slash Commands (`/`)
- Seluruh perintah disinkronkan ke Discord API (`await bot.tree.sync()`).
- **Slash Commands Mandiri:**
  1. `/buka_absen`: Buka sesi absen manual, pin pesan pembukaan dinas, dan tampilkan template absen.
  2. `/tutup_absen`: Tutup sesi absen manual dan kirim pesan penutupan istirahat.
  3. `/rekap`: Rekapitulasi dinas mingguan dengan format Discord Embed dan sistem pemecahan halaman (pagination).
  4. `/tegur` (params: `member`, `pesan`): Kirim Embed Surat Teguran Kedisiplinan Resmi.
  5. `/reject` (params: `member`, `alasan`): Batalkan kehadiran member hari ini seketika.
  6. `/help`: Menampilkan panduan seluruh Slash Commands secara personal (`ephemeral=True`).

- **Command Group Pengaturan (`/config`):**
  1. `/config show`: Tampilkan seluruh pengaturan aktif server dalam bentuk Embed (`ephemeral=True`).
  2. `/config role_absen` (`role`, `aksi: tambah/hapus`): Atur role wajib absen.
  3. `/config role_staff` (`role`, `aksi: tambah/hapus`): Atur role staf pengawas (Admin/Moderator).
  4. `/config jadwal` (`jam_buka`, `jam_tutup`): Atur jam buka dan tutup absensi dinas (WIB).
  5. `/config hari_awal` (`hari`): Atur hari permulaan siklus 7 hari rekapitulasi mingguan.
  6. `/config channel` (`tipe: absensi/rekap`, `channel`): Atur saluran absensi atau rekap.
  7. `/config template` (`jenis: opening/closing/absen/teguran/peringatan`, `teks`): Kustomisasi template pesan dinamis.

### 2.3 Aturan Absensi & Intervensi
- Wajib melampirkan screenshot/foto in-game dan memenuhi format template teks absen.
- Setelah absen disetujui (`✅`), bot otomatis mengirimkan template baru di bawahnya.
- Reaksi silang (`❌`) oleh staf pengawas seketika menghapus catatan database dan menghapus pesan absen terkait.

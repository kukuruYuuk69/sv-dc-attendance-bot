# PRD: Discord Attendance & Automation Bot (Universal & Agnostic Engine)

## 1. Tujuan Proyek
Membuat bot Discord multi-server agnostik, otomatis, dan mandiri berbasis Discord Slash Commands (`/`) serta database konfigurasi dinamis (`attendance.db`). Bot ini mengelola absensi member wajib absen dengan validasi lampiran foto, auto lock/unlock channel, auto-pin pengumuman dinas, layout template standar, konfigurasi multi-role ping dinamis, fitur auto-provisioning channel baru dengan security lock, interactive onboarding wizard, dan rekapitulasi mingguan berhalaman.

## 2. Fitur & Arsitektur Utama

### 2.1 Default Templates Agnostik (Universal)
Semua template bawaan tidak lagi terikat pada instansi atau nama kesatuan tertentu:
- **Opening:** Pemberitahuan pembukaan jam dinas/kehadiran harian standar.
- **Closing:** Pemberitahuan penutupan jam dinas harian standar.
- **Absen:**
  ```text
  📋 **TEMPLATE ABSENSI:**
  ```text
  Nama: 
  Divisi: 
  Status: Hadir
  Ping: <@&ROLE_ID_1> <@&ROLE_ID_2>
  ```
  *(Wajib menyertakan screenshot/foto in-game/bukti kehadiran)*
  ```
- **Teguran:** Surat teguran kedisiplinan resmi agnostik.
- **Peringatan:** Peringatan evaluasi kehadiran agnostik.

### 2.2 Dukungan Multi-Role Ping
- Bot mendukung penyimpanan dan pelampiran lebih dari satu role pada baris `Ping:` maupun pengumuman dinas.
- Disimpan dalam bentuk JSON List ID role (`ping_roles`).

### 2.3 Auto-Provisioning & Channel Security (`on_guild_join`)
Saat bot bergabung ke server baru:
1. Memeriksa keberadaan channel teks yang mengandung kata kunci: `absen`, `attendance`, `rekap`, `report`.
2. Jika tidak ada, bot otomatis membuat dua channel:
   - `attendance`: Saluran pengiriman absensi member.
   - `attendance-report`: Saluran rekapitulasi dinas dengan izin terkunci (`send_messages: False`, `add_reactions: True` bagi role default `@everyone`, hanya Staf/Admin yang bisa mengetik).
3. Mengirimkan **Interactive Onboarding Wizard** ke channel absensi yang baru dibuat khusus untuk Server Owner / Administrator.

### 2.4 Command Group Pengaturan Server (`/config`)
- `/config show`: Tampilkan seluruh konfigurasi server saat ini (`ephemeral=True`).
- `/config ping_role` (`role`, `aksi: tambah/hapus`): Tambah atau hapus role target mention baris ping template absen.
- `/config role_absen` (`role`, `aksi: tambah/hapus`): Tambah atau hapus role wajib absen.
- `/config role_staff` (`role`, `aksi: tambah/hapus`): Tambah atau hapus role staf pengawas (Admin/Mod).
- `/config jadwal` (`jam_buka`, `jam_tutup`): Atur jam buka dan tutup absensi dinas (WIB).
- `/config hari_awal` (`hari`): Atur hari permulaan siklus 7 hari rekap mingguan.
- `/config channel` (`tipe: absensi/rekap`, `channel`): Arahkan saluran absensi atau rekap.
- `/config template` (`jenis`, `teks`): Kustomisasi template teks dinamis.
- `/config reset`: Kembalikan seluruh pengaturan server ke setelan awal default agnostik.

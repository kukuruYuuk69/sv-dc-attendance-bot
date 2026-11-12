# IMPLEMENTATION PLAN: DUPLICATE CHECK, DYNAMIC REFRESH & PENALTY THRESHOLD

Dokumen ini memuat langkah teknis implementasi penegakan anti-double absen, siklus dinamis template, reset member baru, dan konfigurasi ambang batas penalti pada `bot.py` sesuai [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md).

---

## 1. Rencana Perubahan Teknis (`bot.py` & Database)

### 1.1 Penegakan Pencegahan Double Absen Harian (`on_message`)
- **Langkah Kerja:**
  1. Pada event `on_message`, tepat setelah memvalidasi bahwa pengirim memiliki salah satu role di `wajib_absen_roles`:
  2. Ambil tanggal hari ini dalam zona waktu WIB: `today_str = datetime.now(WIB).strftime("%Y-%m-%d")`.
  3. Jalankan query database:
     ```python
     cursor.execute(
         "SELECT 1 FROM attendance WHERE user_id = ? AND date = ?",
         (str(message.author.id), today_str),
     )
     if cursor.fetchone():
       await message.delete()
       await message.channel.send(
           f"⚠️ {message.author.mention} Anda sudah berhasil melakukan absensi"
           f" hari ini ({today_str}). Tidak diperbolehkan mengirim absen"
           " ganda!",
           delete_after=15,
       )
       return
```
  4. Ini mencegah pengiriman pesan ganda sebelum memproses validasi foto atau format teks.

### 1.2 Siklus Pembaruan Template Bersih
- **Langkah Kerja:**
  1. **Saat Absen Disetujui:**
     - Simpan data ke `attendance.db` dan beri reaksi `✅`.
     - Hapus pesan template lama (jika ada tracking ID template terakhir di memory/channel).
     - Kirimkan template absensi baru via `render_attendance_template(cfg)`.
  2. **Saat Intervensi Reaksi Silang (`❌`):**
     - Pada `on_raw_reaction_add`:
       - Hapus catatan dari database `attendance`.
       - Hapus pesan target (`await target_message.delete()`).
       - Kirim pesan pemberitahuan pembatalan (hilang dalam 20 detik).
       - Kirimkan template presensi baru di channel absensi agar anggota dapat langsung menyalin format yang benar.

### 1.3 Skema Database & Perintah `/config ambang_batas`
- **Langkah Kerja:**
  1. Tambahkan kolom ke tabel `guild_config` jika belum ada:
     - `min_attendance_weekly INTEGER DEFAULT 3`
     - `consecutive_threshold INTEGER DEFAULT 2`
  2. Buat sub-command di bawah `config_group`:
     - `/config ambang_batas`
     - Parameter: `minimal_absen: app_commands.Range[int, 1, 7]`, `minggu_beruntun: app_commands.Range[int, 1, 4]`.
     - Simpan ke `guild_config` dan kirim konfirmasi pembaruan secara `ephemeral=True`.
  3. Modifikasi fungsi `build_recap_pages()` agar membaca `min_absen = cfg.get("min_attendance_weekly", 3)` dan `consec_threshold = cfg.get("consecutive_threshold", 2)`.

### 1.4 Command Reset Riwayat Absensi Member Baru (`/reset_user`)
- **Langkah Kerja:**
  1. Buat Slash Command baru:
     - `/reset_user member:@User` (Akses: Hanya Staf / Admin).
  2. Logika Eksekusi:
     - Hapus seluruh riwayat absensi member tersebut dari tabel `attendance`.
     - Hapus riwayat rekap dan catatan pelanggaran dari tabel `weekly_recap` untuk user tersebut.
     - Kirim konfirmasi Embed sukses pembersihan riwayat (Fresh Start) dan catat ke saluran audit log.

---

## 2. Testing Checklist (Daftar Pengujian Unit)

| No. | Skenario Uji | Prosedur Pengujian | Hasil yang Diharapkan |
| :---: | :--- | :--- | :--- |
| 1 | **Double Absen Tertolak** | Kirim absen valid pertama kali, lalu coba kirim absen kedua di hari yang sama. | Pesan kedua langsung **dihapus otomatis**, dan muncul notifikasi peringatan absen ganda selama 15 detik. |
| 2 | **Template Baru Pasca-Absen** | Kirim absen valid. | Pesan diberi centang `✅`, data tercatat, dan pesan template baru otomatis muncul di bawahnya. |
| 3 | **Penolakan via Reaksi Silang** | Staf memberi reaksi `❌` pada pesan absen yang sudah disetujui. | Pesan absen **dihapus seketika**, data dicabut dari database, notifikasi penolakan muncul, dan template baru dikirimkan. |
| 4 | **Pengaturan Ambang Batas** | Jalankan `/config ambang_batas minimal_absen:4 minggu_beruntun:3`. | Ambang batas tersimpan; jalankan `/rekap` untuk memverifikasi standar berubah menjadi minimal 4x. |
| 5 | **Reset Member Baru** | Jalankan `/reset_user member:@User`. | Seluruh data absensi & pelanggaran member terhapus dari SQLite, memberikan status *fresh start*. |

---

## 3. Langkah Komitmen & Konfirmasi
1. Berkas [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md) dan [IMPLEMENTATION.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/IMPLEMENTATION.md) di-commit ke branch `master`.
2. Menunggu konfirmasi persetujuan dari pengguna sebelum mengeksekusi modifikasi di `bot.py`.

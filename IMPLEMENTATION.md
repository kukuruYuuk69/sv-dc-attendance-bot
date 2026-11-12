# IMPLEMENTATION PLAN: ATTENDANCE & AUTOMATION BOT

Dokumen ini menjabarkan rencana teknis, tahapan implementasi kode pada `bot.py`, serta daftar uji verifikasi (*testing checklist*) sesuai spesifikasi [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md).

---

## 1. Rencana Perubahan Teknis (`bot.py`)

### 1.1 Modifikasi Fungsi Pembukaan Absen (`execute_opening`)
- **Tindakan:**
  1. Hapus variabel global `last_pinned_messages`.
  2. Hapus blok kode pencarian pesan lama (`fetch_message`) dan pemanggilan `await old_msg.unpin()`.
  3. Hapus baris pemanggilan `await new_msg.pin()`.
  4. Sederhanakan fungsi: hanya merender teks pengumuman dan template presensi, lalu mengirimkannya via `await channel.send(full_message)`.

### 1.2 Penyesuaian Logika Loop Background Task (`check_dynamic_schedules`)
- **Tindakan:**
  1. Saat waktu sekarang cocok dengan `cfg["close_time"]`:
     - Hitung indeks hari awal `start_idx = DAY_MAP.get(cfg["start_day"].lower(), 0)`.
     - Hitung indeks hari akhir siklus: `end_idx = (start_idx + 6) % 7`.
     - Periksa apakah hari saat ini (`now_wib.weekday() == end_idx`).
  2. Jika hari dan jam cocok:
     - Ambil `rekap_channel` dari `cfg["rekap_channel_id"]`.
     - Jalankan kalkulasi rekap mingguan dan kirimkan Embed laporan rekapitulasi secara otomatis ke saluran tersebut.

### 1.3 Standarisasi Format Mention Interaktif Pengguna
- **Tindakan:**
  1. **Pada Fungsi Rekapitulasi (`/rekap` dan rekap otomatis):**
     - Gunakan format konsisten: `f"✅ **{m.mention}** (`{m.display_name}`): **{count}x** Hadir"`.
     - Format ini memastikan tag `@Member` berwarna biru khas Discord dan memunculkan pop-out profil server ketika diklik.
  2. **Pada Command `/tegur`:**
     - Tampilkan target member sebagai `member.mention` dan display name `member.display_name`.
     - Pejabat pengawas dicantumkan sebagai `interaction.user.mention`.
  3. **Pada Command `/reject`:**
     - Tampilkan target member dan moderator pengawas dengan mention interaktif di saluran absensi dan audit log.

---

## 2. Testing Checklist (Daftar Pengujian Regresi)

| No. | Skenario Uji | Prosedur Pengujian | Hasil yang Diharapkan |
| :---: | :--- | :--- | :--- |
| 1 | **Buka Absen Tanpa Pin** | Jalankan `/buka_absen` di Discord. | Pesan pembukaan dan template terkirim ke channel, tetapi **TIDAK ada pin** yang terpasang di channel. |
| 2 | **Tutup Absen Manual** | Jalankan `/tutup_absen` di Discord. | Pesan penutupan dinas terkirim dengan benar. |
| 3 | **Rekapitulasi On-Demand** | Jalankan `/rekap` di Discord. | Embed rekapitulasi muncul dengan nama pengguna yang dapat diklik (`member.mention`) dan tombol paginasi berfungsi. |
| 4 | **Teguran Resmi** | Jalankan `/tegur member:@User pesan:Uji coba`. | Embed teguran kedisiplinan terkirim dengan tag user yang dapat diklik. |
| 5 | **Pembatalan Absen** | Jalankan `/reject member:@User alasan:Foto salah`. | Absensi hari itu dihapus dan notifikasi pembatalan muncul dengan mention interaktif. |
| 6 | **Pemeriksaan Jadwal Background** | Biarkan scheduler berjalan per menit. | Tidak ada error log pada console dan pembukaan/penutupan berjalan tepat waktu. |

---

## 3. Langkah Komitmen & Konfirmasi
1. Dokumen [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md) dan [IMPLEMENTATION.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/IMPLEMENTATION.md) disimpan di root direktori.
2. Melakukan commit Git dan push ke branch `master`.
3. Menunggu konfirmasi persetujuan dari pengguna sebelum mengeksekusi modifikasi di `bot.py`.

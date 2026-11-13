# IMPLEMENTATION DOCUMENT: AUTO-LOCK & UNLOCK SALURAN ABSENSI

Dokumen teknis ini memuat langkah implementasi perubahan hak akses saluran absensi (`Channel Permission Overwrite`) pada file `bot.py`.

---

## 1. Modifikasi Fungsi Operasional Saluran (`bot.py`)

### 1.1 Fungsi `execute_opening` (Auto-Unlock)
Perbarui fungsi `execute_opening` agar memulihkan hak kirim pesan bagi `@everyone` sebelum mengirimkan template presensi:

```python
async def execute_opening(channel: discord.TextChannel, cfg: dict):
    try:
        # Buka izin kirim pesan untuk role @everyone
        try:
            await channel.set_permissions(
                channel.guild.default_role,
                send_messages=True,
                reason="Sesi absensi dibuka otomatis oleh bot"
            )
        except Exception as e_perm:
            print(f"[PERMISSION] Gagal membuka kunci saluran {channel.name}: {e_perm}")

        open_text = get_rendered_template_text(cfg, "opening", DEFAULT_TEMPLATES["opening"])
        absen_template = render_attendance_template(cfg)
        full_message = f"{open_text}\n\n━━━━━━━━━━━━━━━━━━\n{absen_template}"

        await channel.send(full_message)
        return True
    except Exception as e:
        print(f"Error opening announcement: {e}")
        return False
```

### 1.2 Fungsi `execute_closing` (Auto-Lock)
Perbarui fungsi `execute_closing` agar mencabut hak kirim pesan bagi `@everyone` sebelum/setelah mengirimkan pengumuman penutupan:

```python
async def execute_closing(channel: discord.TextChannel, cfg: dict):
    try:
        close_text = get_rendered_template_text(cfg, "closing", DEFAULT_TEMPLATES["closing"])
        await channel.send(close_text)

        # Kunci izin kirim pesan untuk role @everyone
        try:
            await channel.set_permissions(
                channel.guild.default_role,
                send_messages=False,
                reason="Sesi absensi ditutup otomatis oleh bot"
            )
        except Exception as e_perm:
            print(f"[PERMISSION] Gagal mengunci saluran {channel.name}: {e_perm}")

        return True
    except Exception as e:
        print(f"Error closing announcement: {e}")
        return False
```

---

## 2. Dampak pada Slash Commands & Background Scheduler
- Slash commands `/buka_absen` dan `/tutup_absen` secara otomatis mewarisi perilaku baru ini karena keduanya memanggil `execute_opening` dan `execute_closing`.
- Background task `check_dynamic_schedules` juga langsung mengunci atau membuka saluran secara otomatis saat waktu `open_time` dan `close_time` tercapai tanpa memerlukan perubahan kode loop tambahan.

---

## 3. Daftar Pengujian & Verifikasi (Testing Checklist)

| No | Skenario Uji | Tindakan / Prosedur | Hasil yang Diharapkan |
| :--- | :--- | :--- | :--- |
| 1 | **Tutup Manual (`/tutup_absen`)** | Staf mengeksekusi `/tutup_absen` | Saluran terkunci, `@everyone` tidak dapat mengetik pesan, pengumuman penutupan terkirim. |
| 2 | **Buka Manual (`/buka_absen`)** | Staf mengeksekusi `/buka_absen` | Saluran terbuka kembali, `@everyone` dapat mengetik pesan, template form terkirim di posisi bawah. |
| 3 | **Jadwal Otomatis Jam Tutup** | Jam WIB mencapai `close_time` | Saluran otomatis terkunci tanpa intervensi manusia. |
| 4 | **Jadwal Otomatis Jam Buka** | Jam WIB mencapai `open_time` | Saluran otomatis terbuka kembali tanpa intervensi manusia. |
| 5 | **Hak Akses Bot & Staf** | Saluran dalam status terkunci | Bot dan Administrator tetap dapat mengirim pesan / embed di saluran. |
| 6 | **Penanganan Izin Hilang** | Izin `Manage Channel` bot dicabut | Bot tetap mengirim teks pengumuman dan mencatat peringatan di log konsol tanpa *crash*. |

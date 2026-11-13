# IMPLEMENTATION DOCUMENT: PERBAIKAN BUG AUTO-LOCK SALURAN ABSENSI

Dokumen teknis ini merinci rencana perubahan kode program pada `bot.py` untuk mengatasi isu lolosnya pesan saat sesi absensi terkunci.

---

## 1. Perbaikan Fungsi `update_attendance_channel_permissions`

### 1.1 Konversi Integer & Overwrite Lengkap
Perbarui fungsi `update_attendance_channel_permissions` dengan struktur izin yang lebih ketat:

```python
async def update_attendance_channel_permissions(channel: discord.TextChannel, cfg: dict, is_open: bool):
    guild = channel.guild
    try:
        # 1. Konfigurasi @everyone (Tolak akses baca dan kirim)
        everyone_overwrite = discord.PermissionOverwrite(
            view_channel=False,
            send_messages=False,
            send_messages_in_threads=False,
            create_public_threads=False,
            create_private_threads=False,
            add_reactions=False
        )
        await channel.set_permissions(guild.default_role, overwrite=everyone_overwrite, reason="Privasi saluran absensi")

        # 2. Konfigurasi Bot Me (Akses penuh)
        bot_overwrite = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            manage_messages=True,
            manage_permissions=True
        )
        await channel.set_permissions(guild.me, overwrite=bot_overwrite, reason="Izin penuh bot absensi")

        # 3. Konfigurasi Role Wajib Absen
        for r_item in cfg.get("wajib_absen_roles", []):
            try:
                r_id = int(r_item)
            except (ValueError, TypeError):
                continue

            role = guild.get_role(r_id)
            if not role:
                print(f"[PERMISSION] Role wajib absen ID {r_id} tidak ditemukan di server {guild.name}.")
                continue

            if is_open:
                absen_overwrite = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    send_messages_in_threads=True,
                    attach_files=True,
                    embed_links=True,
                    read_message_history=True
                )
            else:
                absen_overwrite = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=False,
                    send_messages_in_threads=False,
                    create_public_threads=False,
                    create_private_threads=False,
                    add_reactions=False,
                    read_message_history=True
                )

            await channel.set_permissions(role, overwrite=absen_overwrite, reason=f"Sesi absensi: {'BUKA' if is_open else 'TUTUP'}")

        # 4. Konfigurasi Role Staf (Akses monitor & kirim selalu aktif)
        for s_item in cfg.get("staff_roles", []):
            try:
                s_id = int(s_item)
            except (ValueError, TypeError):
                continue

            role = guild.get_role(s_id)
            if role:
                staff_overwrite = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    send_messages_in_threads=True,
                    manage_messages=True,
                    read_message_history=True
                )
                await channel.set_permissions(role, overwrite=staff_overwrite, reason="Izin staf pengawas absensi")

    except discord.Forbidden as e_forbid:
        print(f"[PERMISSION ERROR] Akses ditolak saat mengubah permission di {channel.name}. Pastikan role bot berada di atas role target dan memiliki izin Manage Permissions: {e_forbid}")
    except Exception as e:
        print(f"[PERMISSION ERROR] Gagal memperbarui izin pada {channel.name}: {e}")
```

---

## 2. Sinkronisasi Izin saat Update Konfigurasi Role

Perbarui callback pada `AbsenRoleSelectView`:
- Setelah `update_guild_config(interaction.guild.id, "wajib_absen_roles", selected_ids)` dipanggil:
- Periksa jam saat ini apakah berada di dalam rentang `open_time` s/d `close_time`.
- Panggil `await update_attendance_channel_permissions(absen_channel, cfg, is_open)`.

---

## 3. Checklist Pengujian & Verifikasi

| No | Skenario Uji | Prosedur | Hasil yang Diharapkan |
| :--- | :--- | :--- | :--- |
| 1 | **Integer Cast Verification** | Jalankan loop fungsi dengan data string `["12345"]` | `guild.get_role(12345)` berhasil terpanggil tanpa `None` |
| 2 | **Explicit Close Lock** | Jalankan `/tutup_absen` | User dengan role wajib absen (non-admin) tidak memiliki input teks di saluran |
| 3 | **Thread & Reaction Block** | User mencoba membuat thread atau reaksi saat tutup | Discord memblokir interaksi input teks/thread |
| 4 | **Immediate Role Sync** | Ubah role via `/config role_absen` saat sesi tutup | Role baru yang dipilih langsung terkunci seketika |
| 5 | **Explicit Open Unlock** | Jalankan `/buka_absen` | User dengan role wajib absen dapat mengirim pesan dan lampiran gambar |

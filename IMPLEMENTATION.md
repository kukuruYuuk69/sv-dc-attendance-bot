# IMPLEMENTATION PLAN: PEMBERSIHAN HARDCODE DEFAULT ROLE

Dokumen ini memuat panduan implementasi teknis pembersihan seluruh nilai sisa (*residual*) hardcode role pada `bot.py` sesuai [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md).

---

## 1. Rencana Perubahan Kode Teknis (`bot.py`)

### 1.1 Putus Ketergantungan `.env` untuk Konfigurasi Role
- Di dalam fungsi `get_guild_config()`:
  - **Ubah:**
    ```python
    default_wajib_roles = (
        [int(os.getenv("ROLE_WAJIB_ABSEN_ID"))]
        if os.getenv("ROLE_WAJIB_ABSEN_ID")
        else []
    )
    default_staff_roles = [
        int(r.strip())
        for r in os.getenv("ROLE_MODERATOR_IDS", "").split(",")
        if r.strip()
    ]
    default_ping_roles = []
```
  - **Menjadi:**
    ```python
    default_wajib_roles = []
    default_staff_roles = []
    default_ping_roles = []
    default_absen = 0
    default_rekap = 0
```
  - Ini memastikan bahwa server mana pun yang baru masuk atau di-reset akan selalu memiliki konfigurasi awal yang **bersih tanpa sisa ID server lain**.

### 1.2 Sanitasi Render Role pada `/config show`
- Saat merender string mention role di `/config show`:
  - Periksa apakah role ID tersebut valid dan benar-benar ada di dalam server (`guild.get_role(r_id)`).
  - Abaikan role ID yang menghasilkan `None` (misalnya role sudah dihapus atau role dari server lain).
  - Jika hasil filter kosong: Tampilkan `"Belum diatur"`.

### 1.3 Pembersihan File `.env` Lokal
- Rapikan file `.env` di lingkungan bot agar hanya berisi kredensial bot Discord (`DISCORD_BOT_TOKEN`) dan tidak lagi menyimpan `ROLE_WAJIB_ABSEN_ID` atau ID channel lama.

---

## 2. Testing Checklist (Verifikasi Clean State)

| No. | Skenario Pengujian | Langkah Pengujian | Hasil yang Diharapkan |
| :---: | :--- | :--- | :--- |
| 1 | **Reset Konfigurasi Bersih** | Jalankan `/config reset` di server Discord. | Konfigurasi server ter-reset dan bot mengonfirmasi berhasil. |
| 2 | **Pengecekan Tampilan Awal** | Jalankan `/config show` setelah reset. | - Saluran Absensi: `Belum diatur`<br>- Saluran Rekap: `Belum diatur`<br>- Role Wajib Absen: **`Belum diatur`** (TIDAK ADA `@unknown-role`)<br>- Role Staf Pengawas: **`Belum diatur`**<br>- Role Target Ping: **`Belum diatur`** |
| 3 | **Setup Role via Menu** | Jalankan `/config role_absen` lalu pilih role dari dropdown multi-select. | Role yang dipilih tersimpan dan hanya role tersebut yang muncul di `/config show`. |
| 4 | **Pengecekan Server Baru (`on_guild_join`)** | Simulasi server baru bergabung. | Server otomatis mendapatkan default `wajib_absen_roles: []` dan `staff_roles: []`. |

---

## 3. Langkah Komitmen & Konfirmasi
1. Berkas [REQUIREMENTS.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/REQUIREMENTS.md) dan [IMPLEMENTATION.md](file:///C:/Users/t495s/.gemini/antigravity/scratch/sv-dc-attendance-bot/IMPLEMENTATION.md) di-commit ke branch `master`.
2. Menunggu konfirmasi persetujuan dari pengguna sebelum mengeksekusi kode di `bot.py` dan `.env`.

# IMPLEMENTATION DOCUMENT: GRACEFUL AUTO-EXIT & GITHUB ACTIONS WORKFLOW

Dokumen ini memuat panduan implementasi modul timer *Graceful Auto-Exit* di `bot.py` serta instruksi izin GitHub CLI untuk mempublikasikan file workflow GitHub Actions.

---

## 1. Modifikasi Teknis `bot.py` (Timer Internal 295 Menit)

### 1.1 Implementasi Async Task Lifecycle
Tambahkan coroutine `graceful_shutdown_task` menggunakan `asyncio` yang berjalan di latar belakang sejak bot siap (`on_ready`):

```python
import asyncio

# Durasi operasional aman sebelum runner GitHub Actions mencapai batas timeout (4 jam 55 menit)
RUN_DURATION_MINUTES = 295

async def graceful_shutdown_task():
    await bot.wait_until_ready()
    print(f"[LIFECYCLE] Bot siap. Memulai timer operasional aman: {RUN_DURATION_MINUTES} menit.")
    await asyncio.sleep(RUN_DURATION_MINUTES * 60)
    
    print("[LIFECYCLE] Timer 295 menit tercapai. Melakukan penutupan koneksi bersih...")

    # 1. Hentikan task looping
    if check_dynamic_schedules.is_running():
        check_dynamic_schedules.stop()

    # 2. Tutup koneksi database SQLite secara aman
    try:
        conn.commit()
        conn.close()
        print("[LIFECYCLE] Transaksi SQLite berhasil disimpan dan koneksi ditutup.")
    except Exception as e:
        print(f"[LIFECYCLE] Peringatan saat menutup database: {e}")

    # 3. Putuskan koneksi Discord Gateway
    try:
        await bot.close()
        print("[LIFECYCLE] Koneksi Discord Gateway ditutup dengan sukses (Exit 0).")
    except Exception as e:
        print(f"[LIFECYCLE] Peringatan saat menutup sesi bot: {e}")
```

### 1.2 Registrasi Task pada Event `on_ready`
Pada event `on_ready()`, daftarkan task agar otomatis berjalan saat bot berhasil login:
```python
@bot.event
async def on_ready():
    # ... sinkronisasi slash commands ...
    bot.loop.create_task(graceful_shutdown_task())
```

---

## 2. Otorisasi GitHub CLI & Push Workflow

GitHub secara ketat membatasi modifikasi direktori `.github/workflows/` melalui koneksi OAuth jika token belum memiliki cakupan hak akses (*scope*) `workflow`.

### 2.1 Prosedur Pembaharuan Scope Izin
Jalankan perintah berikut pada terminal PowerShell:

```powershell
# 1. Perbarui scope autentikasi GitHub CLI agar mencakup hak izin workflow
gh auth refresh -s workflow

# 2. Setelah proses otorisasi web selesai, tambahkan file workflow ke staging Git
git add .github/workflows/bot_runner.yml

# 3. Lakukan commit perubahan
git commit -m "ci: add workflow"

# 4. Push workflow ke repositori remote
git push origin master
```

---

## 3. Checklist Verifikasi
- [ ] Task `graceful_shutdown_task` terdaftar di event loop tanpa blocking.
- [ ] `python -m py_compile bot.py` lolos tanpa syntax error.
- [ ] Scope `gh auth status` menampilkan izin `'workflow'`.
- [ ] File `.github/workflows/bot_runner.yml` berhasil terdorong ke remote repository GitHub `master`.
- [ ] Tab Actions di GitHub menampilkan workflow `Discord Attendance Bot Runner` yang aktif.

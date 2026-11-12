# IMPLEMENTATION DOCUMENT: GRACEFUL SHUTDOWN & FREE GIT BACKUP

Dokumen teknis ini memuat langkah implementasi *graceful shutdown* pada `bot.py` serta konfigurasi CI/CD estafet backup pada `.github/workflows/bot_runner.yml`.

---

## 1. Modifikasi Kode Program (`bot.py`)

### 1.1 Penambahan Lifecycle Timer (295 Menit)
Tambahkan background task atau coroutine async yang menghitung durasi sejak `on_ready`:
```python
import asyncio

RUN_DURATION_MINUTES = 295  # 4 Jam 55 Menit

async def graceful_shutdown_task():
    await bot.wait_until_ready()
    print(f"[LIFECYCLE] Bot aktif. Memulai timer estafet graceful shutdown: {RUN_DURATION_MINUTES} menit.")
    await asyncio.sleep(RUN_DURATION_MINUTES * 60)
    
    print("[LIFECYCLE] Waktu estafet 295 menit tercapai. Memulai graceful shutdown...")
    
    # 1. Hentikan loop background task
    if check_dynamic_schedules.is_running():
        check_dynamic_schedules.stop()
        
    # 2. Pastikan transaksi database tersimpan rapi dan koneksi ditutup
    try:
        conn.commit()
        conn.close()
        print("[LIFECYCLE] Database SQLite berhasil dikomit dan ditutup dengan aman.")
    except Exception as e:
        print(f"[LIFECYCLE] Error saat menutup database: {e}")

    # 3. Tutup koneksi Discord Gateway
    try:
        await bot.close()
        print("[LIFECYCLE] Sesi Discord Gateway ditutup secara bersih (Exit Code 0).")
    except Exception as e:
        print(f"[LIFECYCLE] Error saat menutup sesi bot: {e}")
```

Daftarkan coroutine ini di dalam `on_ready()`:
```python
bot.loop.create_task(graceful_shutdown_task())
```

---

## 2. Modifikasi Workflow GitHub Actions (`.github/workflows/bot_runner.yml`)

Workflow diperbarui untuk mengelola *permissions* Git (`contents: write`), langkah restorasi dari branch `db-backup`, dan langkah push otomatis pasca-eksekusi.

### 2.1 Konfigurasi Lengkap YAML
```yaml
name: Discord Attendance Bot Runner

on:
  push:
    branches: [ master ]
  workflow_dispatch:
  schedule:
    # Trigger setiap 5 jam untuk menyambung estafet sebelum bot runner berhenti
    - cron: '0 */5 * * *'

permissions:
  contents: write

jobs:
  run-bot:
    runs-on: ubuntu-latest
    timeout-minutes: 350

    steps:
      - name: Checkout Master Repository
        uses: actions/checkout@v4
        with:
          ref: master
          fetch-depth: 0

      - name: Setup Python Runtime
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Code Syntax & Integrity Check
        run: |
          python -m py_compile bot.py

      - name: Restore SQLite Database from db-backup Branch
        run: |
          # Periksa apakah remote branch db-backup ada
          if git ls-remote --heads origin db-backup | grep -q db-backup; then
            echo "Memulihkan attendance.db dari branch db-backup..."
            git fetch origin db-backup
            git checkout origin/db-backup -- attendance.db || true
            if [ -f attendance.db ]; then
              echo "✅ attendance.db berhasil dipulihkan."
            else
              echo "ℹ️ attendance.db tidak ditemukan di db-backup, inisialisasi baru."
            fi
          else
            echo "ℹ️ Branch db-backup belum ada. Database baru akan dibuat."
          fi

      - name: Execute Discord Bot (Estafet 295 Menit)
        env:
          DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_TOKEN }}
          LOG_CHANNEL_ID: ${{ secrets.LOG_CHANNEL_ID }}
        run: |
          python bot.py

      - name: Backup SQLite Database to db-backup Branch
        if: always()
        run: |
          if [ -f attendance.db ]; then
            echo "Mempersiapkan pencadangan attendance.db ke branch db-backup..."
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            
            # Buat branch db-backup jika belum ada atau beralih ke orphan branch terisolasi
            git checkout --orphan temp-db-backup || git checkout -b temp-db-backup
            git rm -rf . || true
            git checkout master -- .gitignore || true
            
            # Simpan file attendance.db
            git add -f attendance.db
            git commit -m "chore(backup): auto-save attendance.db state [skip ci]" || echo "Tidak ada perubahan data."
            
            # Push ke branch db-backup
            git push origin temp-db-backup:db-backup --force
            echo "✅ Snapshot attendance.db berhasil dicadangkan ke branch db-backup."
          else
            echo "⚠️ File attendance.db tidak ditemukan. Melewati langkah pencadangan."
          fi
```

---

## 3. Matikan Host Bot Lokal
Sebelum workflow Actions aktif secara berkala:
- Jalankan perintah manajemen proses untuk menghentikan daemon bot lokal (`task-682` atau process python yang aktif).
- Memastikan tidak ada token bot yang aktif bersamaan di host lokal.

---

## 4. Daftar Pengujian & Verifikasi (Testing Checklist)

| No | Skenario Uji | Indikator Keberhasilan |
| :--- | :--- | :--- |
| 1 | **Syntax Check** | `python -m py_compile bot.py` berhasil tanpa syntax error. |
| 2 | **Timer Shutdown** | Log mencetak `[LIFECYCLE] Waktu estafet 295 menit tercapai` dan proses keluar dengan status `0`. |
| 3 | **Database Flush** | `conn.commit()` dan `conn.close()` berhasil dijalankan tanpa exception. |
| 4 | **Branch Creation** | Branch `db-backup` otomatis muncul di GitHub setelah run pertama selesai. |
| 5 | **Database Restore** | Runner berikutnya membaca `attendance.db` yang berisi data dari run sebelumnya. |
| 6 | **No Session Conflict** | Host lokal mati, Discord Gateway stabil tanpa warning `Session Invalidated`. |

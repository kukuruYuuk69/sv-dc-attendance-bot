# IMPLEMENTATION DOCUMENT: SETUP CI/CD & RUNNER GITHUB ACTIONS

Dokumen ini menjabarkan panduan teknis langkah demi langkah untuk mengimplementasikan workflow GitHub Actions bagi bot absensi Discord (`sv-dc-attendance-bot`).

---

## 1. Pembuatan Dependensi `requirements.txt`
Sebelum workflow dibuat, repositori harus memiliki file manifest dependensi Python standar:
```text
discord.py>=2.3.0
pytz>=2023.3
python-dotenv>=1.0.0
```

---

## 2. Struktur Direktori & Konfigurasi Workflow YAML
Workflow akan ditempatkan di `.github/workflows/bot_runner.yml`.

### Arsitektur Workflow:
- **Triggers**:
  - `workflow_dispatch`: Memungkinkan admin menjalankan atau me-restart bot secara manual dari tab Actions GitHub.
  - `push` pada branch `master`: Memastikan setiap update kode memicu CI check dan eksekusi.
  - `schedule` (cron): Opsi penjadwalan periodik untuk menjaga kesinambungan bot sebelum batas timeout 6 jam VM GitHub tercapai.

### Contoh Rancangan YAML (`.github/workflows/bot_runner.yml`):
```yaml
name: Discord Attendance Bot Runner

on:
  push:
    branches: [ master ]
  workflow_dispatch:
  schedule:
    # Trigger periodik setiap 5 jam untuk me-refresh runner sebelum batas 6 jam
    - cron: '0 */5 * * *'

jobs:
  run-bot:
    runs-on: ubuntu-latest
    timeout-minutes: 350 # Sedikit di bawah batas absolut 360 menit GitHub

    steps:
      - name: Checkout Repository
        uses: actions/checkout@v4

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

      - name: Restore SQLite Database State (If Cached)
        uses: actions/cache/restore@v4
        with:
          path: attendance.db
          key: attendance-db-${{ github.run_id }}
          restore-keys: |
            attendance-db-

      - name: Execute Discord Bot
        env:
          DISCORD_BOT_TOKEN: ${{ secrets.DISCORD_TOKEN }}
          LOG_CHANNEL_ID: ${{ secrets.LOG_CHANNEL_ID }}
        run: |
          python bot.py

      - name: Save SQLite Database State
        if: always()
        uses: actions/cache/save@v4
        with:
          path: attendance.db
          key: attendance-db-${{ github.run_id }}
```

---

## 3. Panduan Konfigurasi Repository Secrets di GitHub

Admin atau pemilik repositori harus melakukan langkah berikut sebelum workflow dijalankan:

1. Buka repositori `sv-dc-attendance-bot` di browser GitHub:
   `https://github.com/kukuruYuuk69/sv-dc-attendance-bot`
2. Klik tab **Settings** di navigasi atas repository.
3. Pada sidebar sebelah kiri, pilih menu **Secrets and variables** -> **Actions**.
4. Klik tombol hijau **New repository secret**.
5. Masukkan rincian secret:
   - **Name**: `DISCORD_TOKEN`
   - **Secret**: Masukkan token bot Discord dari Discord Developer Portal.
6. (Opsional) Tambahkan secret kedua:
   - **Name**: `LOG_CHANNEL_ID`
   - **Secret**: Masukkan ID channel Discord untuk audit log (misal `123456789012345678`).
7. Klik **Add secret**.

---

## 4. Testing & Verification Checklist

| No | Komponen Uji | Prosedur Pengujian | Hasil yang Diharapkan |
| :--- | :--- | :--- | :--- |
| 1 | **Lint & Compile** | Jalankan `python -m py_compile bot.py` di runner | Exit code 0, tidak ada error sintaks |
| 2 | **Secrets Injection** | Periksa pembacaan `os.getenv("DISCORD_BOT_TOKEN")` | Token terbaca tanpa terpapar di log runner |
| 3 | **Gateway Connection** | Pantau log step eksekusi pada tab Actions | Muncul log `[INFO] discord.client: logging in` dan `connected to Gateway` |
| 4 | **Slash Commands Sync** | Verifikasi respon `bot.tree.sync()` di log Actions | Muncul pesan sinkronisasi seluruh slash commands |
| 5 | **State Retention** | Periksa langkah `actions/cache` saat job selesai | File `attendance.db` tersimpan dan berhasil dipulihkan di run berikutnya |
| 6 | **Manual Trigger** | Jalankan `Run workflow` dari menu Actions tab | Workflow berjalan lancar tanpa intervensi manual |

---

## 5. Tahapan Eksekusi Lanjutan (Menunggu Konfirmasi Pengguna)
1. Pembuatan file `requirements.txt`.
2. Pembuatan direktori `.github/workflows/` dan file workflow `bot_runner.yml`.
3. Verifikasi git status, commit, dan push ke branch `master`.

# REQUIREMENTS DOCUMENT: GRACEFUL AUTO-EXIT & GITHUB ACTIONS WORKFLOW

## 1. Pendahuluan
Dokumen ini menetapkan spesifikasi fungsional untuk pengoperasian bot absensi Discord (`sv-dc-attendance-bot`) di lingkungan GitHub Actions Runner. Pendekatan ini mengutamakan stabilitas sistem, integritas data transaksi absensi, serta pemanfaatan infrastruktur komputasi *Open Source* 100% gratis tanpa perlu registrasi kartu kredit (*No CC*).

---

## 2. Analisis & Kebutuhan Inti

### 2.1 Fitur Pengaman Graceful Auto-Exit (Timer 295 Menit)
- **Konteks & Batasan GitHub Actions:**
  - Runner GitHub Actions memiliki batas durasi per job hingga 360 menit (6 jam). File workflow diatur dengan `timeout-minutes: 350` untuk mencegah runner menggantung tanpa batas.
  - Jika proses dihentikan paksa oleh sistem (*SIGKILL* / timeout), penulisan data pada SQLite dapat tertahan dalam mode *write-ahead log* (WAL) atau *uncommitted transaction*, yang berisiko menyebabkan berkas `attendance.db` korup ketika dicadangkan.
- **Kebutuhan Sistem:**
  - Bot wajib memiliki *lifecycle check* berbasis timer internal (295 menit / 4 jam 55 menit).
  - Saat durasi 295 menit tercapai, bot harus secara proaktif melakukan penghentian anggun (*graceful shutdown*):
    1. Menghentikan loop penjadwalan dinamis (`tasks.loop`).
    2. Menyimpan seluruh transaksi yang tertunda dan menutup koneksi database SQLite (`conn.commit()`, `conn.close()`).
    3. Menutup koneksi Discord Gateway secara formal (`await bot.close()`).
    4. Mengakhiri proses dengan kode keluar sukses (`exit code 0`).
  - Hal ini menjamin bahwa langkah `actions/cache` atau backup data berikutnya di runner GitHub Actions menyimpan file `attendance.db` dalam kondisi bersih (*clean state*).

### 2.2 Pendekatan Open Source 100% Tanpa Kartu Kredit (No CC)
- Seluruh kebutuhan komputasi dan *state retention* bot dipenuhi secara eksklusif menggunakan:
  - **Runner GitHub Actions Publik**: Kuota gratis yang disediakan oleh GitHub untuk repositori tanpa syarat input kartu kredit atau tagihan tersembunyi.
  - **Cron Schedule Estafet**: Jadwal periodik `cron: '0 */5 * * *'` yang menyambung eksekusi runner berikutnya secara otomatis setelah runner sebelumnya berhenti anggun.
  - **GitHub Native Cache / Branch Storage**: Penyimpanan persisten file `attendance.db` tanpa memerlukan server database cloud berbayar.

---

## 3. Matriks Kriteria Penerimaan (Acceptance Criteria)
1. **Pencegahan Data Corruption**: SQLite ditutup dengan `conn.close()` sebelum step pasca-eksekusi runner menyimpan file database.
2. **Estafet Berkesinambungan**: Bot mati secara teratur sebelum batas 350 menit, memungkinkan job workflow sukses (`success`) dan siap disambung oleh jadwal cron berikutnya.
3. **Bebas Biaya**: Tidak melibatkan registrasi platform berbayar pihak ketiga.

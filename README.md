# CERIA SKM – Versi Website (Flask)

Aplikasi web untuk menampilkan dashboard dan mengelola data Survei Kepuasan Masyarakat (SKM) yang tersimpan di Google Sheets.

## Fitur
- Dashboard ringkasan rata-rata per pertanyaan dan per Puskesmas
- Filter Puskesmas (placeholder sederhana)
- Ekspor CSV ringkas & penuh
- Edit dan hapus baris data langsung dari web
- Link ke Google Form + generate data langsung dari sheet

## Struktur Direktori
```
ceria_skm_website/
  requirements.txt
  service_account_info.py        # Isi sendiri dengan JSON service account
  run_server.py
  app/
    __init__.py
    config.py
    sheets.py
    views.py
    templates/
      base.html
      index.html
      dashboard.html
      manage.html
      edit_row.html
    static/
```

## Persiapan
1. Buat / gunakan service account Google Cloud, aktifkan Google Sheets API & Drive API.
2. Share spreadsheet ke email service account sebagai Editor.
3. Buka URL spreadsheet dan ambil ID (bagian setelah `/d/`).
4. Salin file JSON cred ke bentuk dictionary dan isi di `service_account_info.py` pada variabel `SERVICE_ACCOUNT_INFO`.
5. Pastikan variabel `SPREADSHEET_ID` dan `WORKSHEET_NAME` di `app/config.py` sudah benar. Bisa juga override via environment variable:
   - `CERIA_SKM_SPREADSHEET_ID`
   - `CERIA_SKM_WORKSHEET_NAME`
   - `CERIA_SKM_THRESHOLD`

## Instalasi Dependencies
Di PowerShell:
```
cd C:\Users\User\Documents\ceria_skm_website
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Menjalankan Server
```
python run_server.py
```
Lalu buka http://127.0.0.1:5000 di browser.

## Catatan Keamanan
- Jangan commit `service_account_info.py` ke repo publik.
- Atur `debug=False` di produksi.

## TODO / Pengembangan Lanjutan
- Autentikasi admin (login)
- Pagination & pencarian data manage
- Caching agar tidak selalu memanggil API Sheets
- Grafik tambahan (tren waktu, distribusi skor)
- API v2 dengan filtering server-side

Selamat menggunakan!

---

## Deployment ke GitHub & Docker

### 1. Struktur Kredensial Aman
- File asli `service_account_info.py` tidak di-commit (`.gitignore`).
- Commit hanya `service_account_info.example.py`.
- Alternatif: gunakan environment variable `CERIA_SKM_SERVICE_ACCOUNT_JSON` (isi seluruh JSON dalam satu baris / raw secret GitHub) — kode otomatis mem-parsing ketika dict lokal kosong.

### 2. Build Lokal Docker
```
docker build -t ceria-skm:latest .
docker run -p 8000:8000 -e CERIA_SKM_SPREADSHEET_ID=ID_SPREADSHEET \
  -e CERIA_SKM_SERVICE_ACCOUNT_JSON="$(cat credentials.json)" ceria-skm:latest
```

### 3. GitHub Actions (CI)
Workflow `.github/workflows/docker-build.yml` otomatis build & push image ke GHCR saat push ke `main` atau `master`.

Image name: `ghcr.io/ceriaskm48-cell/ceriaApp:<tag>` (secara otomatis diisi oleh workflow karena menggunakan `${{ github.repository }}`)

### 4. Menambahkan Secrets di GitHub Repository Settings
Pergi ke: Settings → Secrets and variables → Actions → New repository secret.

Disarankan secrets:
- `CERIA_SKM_SPREADSHEET_ID`
- `CERIA_SKM_SERVICE_ACCOUNT_JSON` (isi full JSON). Pastikan newline di private_key tetap berupa `\n` (GitHub secret raw copy dari file JSON sudah sesuai).

Kemudian Anda bisa override di deployment (misal di platform container) dengan environment variable tersebut.

### 5. Menjalankan Container di Server / VPS
```
docker run -d --name ceria-skm -p 8000:8000 \
  -e CERIA_SKM_SPREADSHEET_ID=ID_SPREADSHEET \
  -e CERIA_SKM_SERVICE_ACCOUNT_JSON="$(cat service_account.json)" \
  ghcr.io/ceriaskm48-cell/ceriaApp:latest
```
Lalu pasang reverse proxy (Nginx / Caddy) mengarah ke port 8000.

### 6. Tambahan Hardening Produksi
- Set `gunicorn` workers sesuai CPU (misal `--workers 4`).
- Matikan debug Flask (sudah otomatis karena pakai Gunicorn).
- Rate limiting (opsional) → gunakan proxy atau library extension.
- Caching READ-only data (misal layer depan dengan Cloudflare atau internal in-memory TTL 60 detik).

### 7. Roadmap Tambahan (Opsional)
- Auth admin (Flask-Login + sederhana).
- Pagination manage view.
- Grafik tren berdasarkan timestamp.
- Export ke XLSX.
- Notifikasi (webhook) saat threshold turun.

### 8. Langkah Push Pertama ke Repo `ceriaskm48-cell/ceriaApp`
Jika direktori ini belum menjadi repo git:
```
git init
git add .
git commit -m "Inisialisasi CERIA SKM Web"
git branch -M main
git remote add origin https://github.com/ceriaskm48-cell/ceriaApp.git
git push -u origin main
```

Setelah push pertama, workflow Actions akan otomatis membangun image dan mendorong ke `ghcr.io/ceriaskm48-cell/ceriaApp:latest` (dan tag lain sesuai metadata).

---

## GitHub Pages (Snapshot Statis)
GitHub Pages tidak bisa menjalankan Flask secara dinamis, tetapi kita menyediakan workflow `pages-snapshot.yml` untuk menghasilkan versi read-only yang otomatis membangun direktori `docs/` dari Google Sheets.

### Cara Mengaktifkan
1. Tambahkan Secrets repo (Settings → Secrets and variables → Actions):
  - `CERIA_SKM_SERVICE_ACCOUNT_JSON`  (isi full JSON service account)
  - `CERIA_SKM_SPREADSHEET_ID`        (ID spreadsheet)
  - `CERIA_SKM_WORKSHEET_NAME`        (nama worksheet; default `Form Responses 2`)
2. (Opsional) Tambah Repository Variable: `CERIA_SKM_FORM_URL` untuk override link form.
3. Pastikan file `.github/workflows/pages-snapshot.yml` ada di branch `main`.
4. Settings → Pages → Source: Deploy from branch → pilih `main` dan folder `docs`.
5. Trigger build: push ke `main` atau gunakan *Run workflow* di tab Actions.
6. Akses: `https://<username>.github.io/<repo>/` → memuat `index.html` snapshot.

### Isi Snapshot
| File | Fungsi |
|------|--------|
| index.html | Ringkasan, QR, link dashboard |
| dashboard.html | Chart interaktif memuat data dari `data.json` |
| data.json | Data hasil ekstraksi & perhitungan rata-rata |
| summary.csv | Ringkasan per pertanyaan + overall |
| full.csv | Semua baris mentah sheet |
| qr.png | Kode QR form Google |
| style.css | Gaya visual sederhana (disalin dari app) |

### Keterbatasan Snapshot
- Tidak ada endpoint edit / delete / export dinamis.
- Data hanya diperbarui saat workflow jalan (push atau jadwal 6 jam).
- Jangan menaruh kredensial dalam file statis; service account hanya dipakai runtime di Actions.

### Menjalankan Snapshot Manual (Lokal)
```
python generate_static_site.py
# Hasil di ./docs
```

Kemudian Anda bisa membuka `docs/index.html` langsung di browser (tanpa server) untuk verifikasi.

---


# Rekomendasi Buku

Web sistem rekomendasi buku berbasis Django dengan tiga metode: **Content-Based Filtering**, **Collaborative Filtering**, dan **Hybrid**, ditambah halaman evaluasi yang menjelaskan prosesnya langkah demi langkah.

## Kebutuhan

- Python **3.11, 3.12, atau 3.13** (disarankan 3.12)
- Tidak perlu install database. Data buku sudah tersedia di file SQLite `rekomendasi-buku`.

## Cara menjalankan

Jalankan semua perintah dari folder yang berisi `manage.py`.

### Windows (PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Jika muncul error `running scripts is disabled`, jalankan sekali:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Buka **http://127.0.0.1:8000**. Hentikan server dengan `Ctrl+C`.
Setiap membuka terminal baru, aktifkan venv dulu (langkah ke-2) sebelum `runserver`.

## Perintah lain

| Perintah | Fungsi |
|---|---|
| `python manage.py createsuperuser` | Membuat akun admin untuk `/admin` |
| `python manage.py import_books` | Mengisi/memperbarui data buku dari `sistem/data/gabungan_buku.csv` |
| `python manage.py update_book_covers` | Mengambil sampul dari Google Books untuk buku yang belum punya sampul |
| `python manage.py test sistem` | Menjalankan tes otomatis |

Pengaturan opsional (secret key, mode debug, API key Google Books) bisa diisi di file `.env`. Lihat `.env.example`.

## Struktur project

```
rekomendasi_buku/            pengaturan Django (settings, urls)
sistem/
  recommendation_service.py  logika Content-Based, Collaborative, Hybrid, dan evaluasi
  genres.py                  normalisasi teks genre
  views.py, urls.py, forms.py, models.py
  data/gabungan_buku.csv     dataset peminjaman buku
  ml_model/                  model content-based (books_list.pkl, similarity.pkl)
  templates/sistem/          halaman; partials/ berisi komponen yang dipakai bersama
  static/                    CSS, JavaScript, gambar
rekomendasi-buku             database SQLite
```

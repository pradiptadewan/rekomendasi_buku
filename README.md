# Rekomendasi Buku

Aplikasi web untuk menjelajahi koleksi buku dan mendapatkan rekomendasi buku dengan tiga metode: **Content-Based Filtering**, **Collaborative Filtering**, dan **Hybrid**. Ada juga halaman **Evaluasi** yang menguraikan cara setiap metode menghasilkan rekomendasi, lengkap dengan skornya.

Dibangun dengan **Django 5.2** (Python), **pandas**, **NumPy**, dan **scikit-learn**. Database memakai **SQLite**, jadi tidak perlu install server database apa pun.

> 📘 **Untuk presentasi skripsi**, baca [PANDUAN_SKRIPSI.md](PANDUAN_SKRIPSI.md): penjelasan data, rumus, contoh hitungan nyata, skenario demo, pertanyaan penguji, keterbatasan, dan saran pengembangan.

---

## Fitur

| Halaman | URL | Keterangan |
|---|---|---|
| Beranda | `/` | Ringkasan dataset, pilihan metode, buku populer |
| Dashboard | `/dashboard/` | Pencarian, genre populer, buku terpopuler dan rating tertinggi |
| Koleksi | `/books/` | Semua buku: cari judul/penulis, filter genre, urutkan, per halaman |
| Detail buku | `/books/<id>/` | Info lengkap, sinopsis, tombol favorit, dan buku serupa |
| Favorit | `/favorites/` | Buku yang disimpan pengguna (harus login) |
| Rekomendasi | `/recommend/` | Pilihan metode rekomendasi |
| Content-Based | `/recommend/content-based/` | Buku mirip judul tertentu, atau saring berdasarkan genre, rating, dan halaman |
| Collaborative | `/recommend/collaborative/` | Rekomendasi untuk seorang pembaca dari dataset |
| Hybrid | `/recommend/hybrid/` | Gabungan Collaborative dan profil genre |
| Evaluasi | `/recommend/evaluation/` | Uraian langkah dan skor ketiga metode |
| Login / Daftar | `/login/`, `/register/` | Akun pengguna web |
| Admin | `/admin/` | Kelola data buku dan favorit (khusus superuser) |

> **Ada dua jenis "pengguna", jangan tertukar.**
> - **Pembaca dataset** (contoh: `@cahayailahiy`) berasal dari data peminjaman di CSV. Mereka dipakai oleh metode Collaborative dan Hybrid.
> - **Pengguna web** adalah orang yang mendaftar lewat halaman Daftar. Mereka hanya dipakai untuk fitur Favorit.

---

## Sumber data

| File | Isi | Dipakai untuk |
|---|---|---|
| `sistem/data/gabungan_buku.csv` | 1.879 baris riwayat peminjaman: `kode, username, status, judul, penulis, rating, jml hlm, genre, sinopsis` | Collaborative, Hybrid, filter Content-Based |
| `sistem/ml_model/books_list.pkl` | Daftar 305 judul beserta teks fitur (judul + penulis) | Content-Based |
| `sistem/ml_model/similarity.pkl` | Matriks kemiripan antar buku, ukuran 305 × 305 | Content-Based |
| `rekomendasi-buku` | Database SQLite: tabel buku (termasuk URL sampul), akun pengguna, favorit | Semua halaman |

Status peminjaman diubah menjadi **skor interaksi**: `Borrowing` (sedang dipinjam) = 3, `Borrowed` (sudah dipinjam) = 2, `Queue` (antre) = 1.

---

## Cara kerja metode rekomendasi

Semua logika ada di `sistem/recommendation_service.py`. Data dimuat sekali saat pertama kali dibutuhkan, lalu disimpan di memori.

### 1. Content-Based Filtering
- **Berdasarkan judul:** mengambil 5 buku dengan skor tertinggi di `similarity.pkl` untuk judul yang dipilih. Kalau skornya sama, buku dengan genre lebih mirip lalu rating lebih tinggi didahulukan.
- **Berdasarkan filter:** menyaring buku menurut genre (dicocokkan utuh, jadi "fiksi" tidak ikut "nonfiksi"), rating minimal, dan jumlah halaman maksimal. Hasil diurutkan berdasarkan jumlah genre yang cocok, lalu rating.

### 2. Collaborative Filtering
1. Membuat matriks *pembaca × buku* berisi skor interaksi.
2. Menghitung kemiripan antar pembaca dengan *cosine similarity*.
3. Mengambil 5 pembaca paling mirip (skor > 0).
4. Menjumlahkan skor buku yang mereka pinjam, kecuali buku yang sudah dipinjam pembaca target. Lima teratas menjadi rekomendasi.

### 3. Hybrid
1. **Kandidat:** 25 buku teratas dari 24 pembaca paling mirip (cara yang sama seperti Collaborative).
2. **Profil genre:** 3 genre yang paling sering muncul di riwayat pinjam pembaca.
3. **Pengurutan ulang:** `skor = jumlah genre favorit yang cocok + 0,2 × rating`. Lima teratas menjadi rekomendasi.

---

## Struktur project

```
rekomendasi_buku/                 ← folder utama (berisi manage.py)
├── manage.py                     perintah Django (runserver, migrate, dll.)
├── requirements.txt              daftar library Python
├── rekomendasi-buku              database SQLite
├── .env.example                  contoh pengaturan opsional
├── rekomendasi_buku/             pengaturan project
│   ├── settings.py               konfigurasi (database, bahasa, login, dll.)
│   └── urls.py                   URL utama
└── sistem/                       aplikasi utama
    ├── models.py                 tabel database: Book, Favorite
    ├── views.py                  logika tiap halaman
    ├── urls.py                   daftar URL halaman
    ├── forms.py                  form login dan daftar
    ├── recommendation_service.py algoritma rekomendasi dan evaluasi
    ├── genres.py                 merapikan teks genre
    ├── context_processors.py     data favorit untuk semua halaman
    ├── admin.py                  tampilan halaman admin
    ├── tests.py                  tes otomatis
    ├── data/                     dataset CSV
    ├── ml_model/                 model Content-Based (.pkl)
    ├── migrations/               riwayat perubahan struktur database
    ├── management/commands/      perintah tambahan (import_books, update_book_covers)
    ├── templates/sistem/         halaman HTML
    │   └── partials/             komponen yang dipakai bersama (navbar, kartu buku, form, dll.)
    └── static/                   CSS, JavaScript, gambar
```

**Alur sebuah permintaan:** browser membuka URL → `urls.py` menentukan fungsi di `views.py` → view mengambil data dari database (`models.py`) atau dari `recommendation_service.py` → hasilnya ditampilkan lewat template HTML.

---

## Cara menjalankan

### Kebutuhan
- **Python 3.11, 3.12, atau 3.13** (disarankan 3.12). Unduh di [python.org](https://www.python.org/downloads/); saat install di Windows, centang **Add python.exe to PATH**.
- **Git**, untuk mengambil kode dari GitHub.

Semua perintah dijalankan dari folder yang berisi `manage.py`.

### Pertama kali (setup awal)

**Windows (PowerShell):**
```powershell
git clone https://github.com/pradiptadewan/rekomendasi_buku.git
cd rekomendasi_buku
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

**macOS / Linux:**
```bash
git clone https://github.com/pradiptadewan/rekomendasi_buku.git
cd rekomendasi_buku
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Buka **http://127.0.0.1:8000**. Hentikan server dengan `Ctrl+C`.

### Menjalankan lagi tanpa perubahan kode

```powershell
.venv\Scripts\Activate.ps1      # macOS/Linux: source .venv/bin/activate
python manage.py runserver
```

### Menjalankan setelah ada perubahan kode

Kalau perubahannya dari GitHub:
```powershell
git pull
.venv\Scripts\Activate.ps1      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Kalau kamu sendiri mengubah `models.py`, buat migrasinya dulu:
```powershell
python manage.py makemigrations
python manage.py migrate
```

Selama server berjalan, perubahan file `.py` dan `.html` dimuat ulang otomatis; cukup refresh browser (untuk CSS/JS tekan `Ctrl+F5`).

### Perintah lain

| Perintah | Fungsi |
|---|---|
| `python manage.py createsuperuser` | Membuat akun admin untuk `/admin` |
| `python manage.py import_books` | Mengisi/memperbarui tabel buku dari CSV |
| `python manage.py update_book_covers` | Mengambil sampul dari Google Books untuk buku yang belum punya sampul |
| `python manage.py test sistem` | Menjalankan tes otomatis |

### Pengaturan opsional (`.env`)

Salin `.env.example` menjadi `.env`. Untuk development, semua isinya boleh dikosongkan.

| Variabel | Fungsi |
|---|---|
| `DJANGO_SECRET_KEY` | Kunci rahasia Django (wajib diganti saat online) |
| `DJANGO_DEBUG` | `True` untuk development, `False` untuk produksi |
| `DJANGO_ALLOWED_HOSTS` | Domain yang diizinkan, dipisah koma |
| `GOOGLE_BOOKS_API_KEY` | API key Google Books untuk `update_book_covers` |

---

## Masalah umum

| Masalah | Solusi |
|---|---|
| `running scripts is disabled` (Windows) | Jalankan sekali: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| `No module named 'django'` | Venv belum aktif (harus ada `(.venv)` di awal baris), atau `pip install -r requirements.txt` belum dijalankan |
| `py` tidak dikenali | Ganti `py -3.12` dengan `python` |
| Folder `.venv` tidak bisa dihapus | Hentikan server, jalankan `deactivate`, tutup PyCharm/VS Code, lalu `cmd /c "rmdir /s /q .venv"` |
| `git pull` gagal karena *local changes* | Periksa dulu file apa yang berubah (`git status`) sebelum menimpanya, terutama file database `rekomendasi-buku` |
| Halaman kosong tanpa buku | Jalankan `python manage.py import_books` |
| Tampilan tidak berubah setelah update | Tekan `Ctrl+F5` di browser |

> Folder `.venv` tidak disimpan di Git. Setiap komputer harus membuat venv sendiri dengan langkah setup awal di atas.

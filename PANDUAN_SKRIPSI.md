# Panduan Memahami & Mempresentasikan Project

Dokumen ini untuk orang yang akan **mempresentasikan project ini di sidang skripsi**. Isinya: data yang dipakai, cara kerja tiap metode lengkap dengan contoh hitungan dari data asli, skenario demo, pertanyaan yang mungkin diajukan penguji, keterbatasan, dan saran pengembangan.

Untuk cara instalasi dan menjalankan aplikasi, lihat [README.md](README.md).

---

## 1. Ringkasan

**Masalah:** pembaca kesulitan memilih buku berikutnya dari banyak pilihan.
**Solusi:** sistem rekomendasi berbasis web yang menyarankan buku dengan tiga pendekatan:

| Metode | Pertanyaan yang dijawab | Data yang dipakai |
|---|---|---|
| **Content-Based Filtering** | "Buku apa yang mirip dengan buku ini?" | Atribut buku (judul, penulis, genre, rating, halaman) |
| **Collaborative Filtering** | "Pembaca yang seleranya mirip denganku membaca apa?" | Riwayat peminjaman antar pembaca |
| **Hybrid** | Gabungan keduanya | Riwayat peminjaman + genre |

Aplikasi juga punya **halaman Evaluasi** yang menampilkan langkah dan skor setiap metode, sehingga proses rekomendasi bisa dijelaskan, tidak sekadar "kotak hitam".

---

## 2. Data

Sumber: `sistem/data/gabungan_buku.csv`. Satu baris = satu pembaca berinteraksi dengan satu buku.

| Kolom | Contoh |
|---|---|
| `kode` | A01 |
| `username` | @cahayailahiy |
| `status` | Borrowing / Borrowed / Queue |
| `judul`, `penulis` | 86, Okky Madasari |
| `rating`, `jml hlm` | 3.74, 256 |
| `genre` | fiksi, keluarga, kriminal |
| `sinopsis` | teks |

**Statistik penting** (hafalkan, sering ditanyakan):

| Angka | Nilai |
|---|---|
| Baris data | 1.879 (1.876 interaksi valid) |
| Buku unik | 305 |
| Pembaca dengan interaksi valid | 260 |
| Genre unik (setelah dirapikan) | 74 |
| Ukuran matriks pembaca × buku | 260 × 305 = 79.300 sel |
| Sel yang terisi | 1.863 (**2,35%**). Data sangat *sparse* (jarang) |
| Median jumlah buku per pembaca | 4 (maksimum 46) |
| Pembaca yang hanya meminjam 1 buku | 68 |

### Pra-pemrosesan
1. **Status → skor interaksi** (semakin tinggi, semakin kuat minatnya):
   `Borrowing` (sedang dipinjam) = **3**, `Borrowed` (sudah dipinjam) = **2**, `Queue` (antre) = **1**.
   Status `No Response` dan `Skipped` dianggap bukan interaksi.
2. **Salah ketik status** di dataset (`Borrowd`, `Boorowed`, `Borrowes`, `Borrowied`) dikoreksi menjadi `Borrowed`.
3. **Genre dirapikan:** huruf kecil, duplikat dibuang, dan genre yang komanya hilang dipisah (`romansayoung-adult misteri` → `romansa, young-adult, misteri`).
4. Jika satu pembaca punya beberapa baris untuk buku yang sama, diambil skor tertingginya.

---

## 3. Cara Kerja Metode

### 3.1 Content-Based Filtering

**Ide:** buku yang deskripsinya mirip kemungkinan disukai oleh pembaca yang sama.

**Langkah:**
1. Setiap buku diwakili teks gabungan **judul + penulis** (kolom `tags` di `books_list.pkl`).
2. Teks diubah menjadi vektor angka dengan **TF-IDF** (*Term Frequency – Inverse Document Frequency*):
   - **TF:** seberapa sering kata muncul di teks buku itu.
   - **IDF:** kata yang jarang muncul di seluruh koleksi mendapat bobot lebih besar.
   - Rumusnya: `TF-IDF(kata, buku) = TF × IDF`. Vektor setiap buku lalu dinormalisasi sehingga panjangnya 1.
3. Kemiripan antar buku dihitung dengan **cosine similarity**:

   ```
   cos(A, B) = (A · B) / (|A| × |B|)
   ```
   Hasilnya 0 sampai 1: 0 = tidak ada kata yang sama, 1 = identik.
4. Hasil perhitungan disimpan sebagai matriks 305 × 305 di `similarity.pkl`. Rekomendasi = 5 buku dengan skor tertinggi.
5. Jika skornya sama (termasuk 0), buku yang **genrenya lebih mirip** (*Jaccard*: jumlah genre yang sama ÷ total genre gabungan), lalu **rating lebih tinggi**, didahulukan.

**Contoh nyata: "86" vs "Maryam"** (keduanya karya Okky Madasari)

| Kata | Bobot di "86" | Bobot di "Maryam" |
|---|---|---|
| 86 | 0,640 | 0 |
| maryam | 0 | 0,640 |
| okky | 0,543 | 0,543 |
| madasari | 0,543 | 0,543 |

`cos = 0,543×0,543 + 0,543×0,543 = 0,59` → **Maryam** menjadi rekomendasi #1 untuk "86", diikuti *Pasung Jiwa* (0,50) dan *Mata dan Nyala Api Purba* (0,38), yang semuanya karya penulis yang sama.

**Mode filter:** pengguna memilih genre, rating minimal, dan halaman maksimal. Buku yang lolos diurutkan berdasarkan jumlah genre yang cocok, lalu rating.

### 3.2 Collaborative Filtering (user-based)

**Ide:** jika dua pembaca meminjam buku-buku yang sama, mereka kemungkinan punya selera yang mirip. Buku yang dipinjam salah satunya bisa direkomendasikan ke yang lain.

**Langkah:**
1. Bentuk **matriks pembaca × buku** berisi skor interaksi (0 jika tidak pernah berinteraksi).
2. Hitung **cosine similarity** antar baris (antar pembaca).
3. Ambil **5 pembaca paling mirip** (skor > 0), yang disebut *tetangga*.
4. Untuk setiap buku yang **belum** dipinjam pembaca target, jumlahkan skor interaksi para tetangga terhadap buku itu.
5. **5 buku dengan jumlah tertinggi** = rekomendasi.

**Contoh nyata: pembaca `@elsa.manalu`**

Riwayatnya 9 buku: *Hati yang Gembira Adalah Obat* (3), *Girls in The Dark* (2), dan 7 buku berstatus antre (masing-masing 1).

Kemiripan dengan `@tomatrare_`, yang meminjam 6 buku termasuk *Girls in The Dark* (skor 3):

```
A · B = 2 × 3 = 6                (satu-satunya buku yang sama: Girls in The Dark)
|A|   = √(3² + 2² + 7×1²) = √20 = 4,47
|B|   = √(3² + 5×1²)      = √14 = 3,74
cos   = 6 / (4,47 × 3,74) = 0,359
```

Lima tetangga teratas: @tomatrare_ (0,359), @cahayailahiy (0,310), @winsforyaa (0,310), @poetstories (0,248), @cepethilang (0,224).
Rekomendasi #1: *Cerita-Cerita Bahagia, Hampir Seluruhnya* (skor 4, dipinjam 2 dari 5 tetangga).

### 3.3 Hybrid (cascade / re-ranking)

**Ide:** Collaborative menghasilkan kandidat dari perilaku pembaca lain, lalu Content-Based (genre) mengurutkan ulang kandidat tersebut agar sesuai selera pribadi.

**Langkah:**
1. **Kandidat:** sama seperti Collaborative, tetapi dengan 24 tetangga, lalu diambil **25 buku kandidat**.
2. **Profil genre:** hitung genre yang paling sering muncul di riwayat pembaca, lalu ambil **3 teratas**.
3. **Skor akhir** setiap kandidat:
   ```
   skor = (jumlah genre favorit yang cocok) + 0,2 × rating
   ```
4. **5 skor tertinggi** = rekomendasi.

**Contoh nyata: `@elsa.manalu`**
- Genre di riwayat: fiksi (7), thriller (6), misteri (6), lalu horor dan kriminal (2). Profil = **fiksi, thriller, misteri**.
- Rekomendasi #1: *A Good Girl's Guide to Murder (ENG)*, yang cocok dengan 3 genre dan berating 4,32:
  `skor = 3 + 0,2 × 4,32 = 3,864`

Bobot 0,2 membuat rating hanya menjadi **penentu urutan di antara buku yang jumlah genre cocoknya sama** (rating maksimal 5 × 0,2 = 1, setara dengan satu genre).

---

## 4. Arsitektur Aplikasi

Django memakai pola **MVT (Model – View – Template)**:

```
Browser ─► urls.py ─► views.py ─┬─► models.py (database SQLite: buku, akun, favorit)
                                └─► recommendation_service.py (CSV + model .pkl)
                     ◄─ template HTML ◄─┘
```

- **Model** (`models.py`): tabel `Book` dan `Favorite`; akun memakai sistem bawaan Django.
- **View** (`views.py`): menerima permintaan, memanggil logika, dan memilih template.
- **Template** (`templates/sistem/`): tampilan HTML; komponen berulang ada di `partials/`.
- **Service** (`recommendation_service.py`): semua algoritma. Data dimuat sekali lalu disimpan di memori, sehingga respons cepat.

**Dua jenis pengguna:** *pembaca dataset* (dipakai algoritma) berbeda dengan *pengguna web* yang mendaftar (hanya untuk fitur Favorit).

---

## 5. Skenario Demo (± 7 menit)

1. **Beranda:** tunjukkan statistik (305 buku, 260 pembaca, 74 genre) dan tiga metode.
2. **Koleksi:** cari "okky", filter genre "misteri", buka satu detail buku, lalu tunjukkan bagian *Buku serupa*.
3. **Content-Based:** cari judul `86`; hasilnya karya Okky Madasari. Pindah ke tab *Saring preferensi*: genre fiksi + misteri, rating ≥ 4.
4. **Collaborative:** pembaca `@elsa.manalu`; jelaskan riwayat di kiri dan rekomendasi di kanan.
5. **Hybrid:** pembaca yang sama; bandingkan hasilnya dengan Collaborative.
6. **Evaluasi → tab Hybrid:** jelaskan tahap 1 (kandidat), 2 (profil genre), dan 3 (tabel skor akhir).
7. **Login → favoritkan buku → halaman Favorit:** tunjukkan fitur pengguna.

Siapkan aplikasi sudah berjalan sebelum sidang dimulai, dan buka tab-tab di atas lebih dulu.

---

## 6. Pertanyaan Penguji yang Mungkin Muncul

**Kenapa memakai cosine similarity, bukan jarak Euclidean?**
Cosine mengukur kesamaan *arah/pola*, bukan besar nilai. Pembaca yang meminjam 40 buku tetap bisa dinilai mirip dengan pembaca yang meminjam 5 buku jika polanya sama. Euclidean akan menganggap keduanya jauh hanya karena jumlah bukunya berbeda.

**Kenapa memakai TF-IDF, bukan hitungan kata biasa?**
TF-IDF menurunkan bobot kata yang umum dan menaikkan kata yang khas. Nama penulis yang jarang muncul jadi penanda kuat kemiripan.

**Apa itu cold start, dan bagaimana sistem ini menanganinya?**
Cold start adalah kondisi pembaca atau buku baru tanpa riwayat, sehingga Collaborative tidak bisa bekerja. Untuk situasi ini sistem menyediakan Content-Based (cukup memilih judul atau filter), yang tidak membutuhkan riwayat.

**Kenapa ada pembaca yang tidak mendapat rekomendasi Collaborative?**
Data sangat sparse (2,35% terisi) dan 68 pembaca hanya meminjam 1 buku. Jika para tetangganya tidak meminjam buku lain, tidak ada kandidat. Ini keterbatasan data, bukan kesalahan program.

**Kenapa skor interaksi 3, 2, 1?**
Status mencerminkan tingkat minat: sedang meminjam (minat paling aktif) > sudah meminjam > masih antre. Ini adalah *implicit feedback*, karena tidak ada rating eksplisit dari tiap pembaca.

**Kenapa Hybrid memakai bobot 0,2 untuk rating?**
Agar kecocokan genre tetap menjadi faktor utama, dan rating hanya menjadi pembeda di antara buku dengan jumlah kecocokan genre yang sama.

**Bagaimana mengukur bahwa rekomendasinya bagus?**
Halaman Evaluasi saat ini bersifat **penjelasan (explainability)**: ia menunjukkan alasan dan skor. Pengukuran akurasi kuantitatif (Precision@K, Recall@K) adalah pengembangan berikutnya (lihat bagian 8).

**Apa perbedaan user-based dan item-based Collaborative Filtering?**
User-based (yang dipakai di sini) mencari *pembaca* yang mirip. Item-based mencari *buku* yang sering dipinjam bersama.

---

## 7. Keterbatasan (sampaikan dengan jujur)

1. **Fitur Content-Based hanya judul + penulis.** Akibatnya, kemiripan tinggi hampir selalu berarti penulis sama. 225 dari 305 buku memiliki kurang dari 5 buku dengan skor kemiripan di atas 0, dan sisanya diurutkan berdasarkan genre.
2. **Stop words bahasa Inggris** dipakai pada TF-IDF, padahal sebagian besar judul berbahasa Indonesia, sehingga kata umum seperti "dan" atau "yang" tidak tersaring.
3. **Data sparse** (2,35%) dan banyak pembaca dengan riwayat sangat sedikit, sehingga Collaborative kurang optimal untuk pembaca tersebut.
4. **Belum ada evaluasi akurasi kuantitatif.**
5. **Pengguna web belum mendapat rekomendasi personal.** Favorit mereka belum dipakai oleh algoritma; Collaborative dan Hybrid hanya untuk pembaca dataset.
6. **Model statis:** jika data bertambah, `similarity.pkl` harus dibuat ulang secara manual.

---

## 8. Saran Pengembangan Selanjutnya

Diurutkan dari yang **paling berdampak untuk nilai skripsi**.

### A. Evaluasi kuantitatif (prioritas utama)
- Bagi data menjadi **data latih dan data uji** (misalnya *leave-one-out*: sembunyikan satu buku dari riwayat tiap pembaca, lalu cek apakah buku itu muncul di rekomendasi).
- Hitung **Precision@5, Recall@5, Hit Rate, dan NDCG** untuk ketiga metode, lalu sajikan dalam tabel perbandingan. Ini menjawab pertanyaan "metode mana yang terbaik?" dengan angka.
- Tampilkan hasilnya di halaman Evaluasi.

### B. Peningkatan algoritma
- **Perkaya fitur Content-Based:** gabungkan judul + penulis + **genre + sinopsis**. Pakai **stop words bahasa Indonesia** dan *stemming* (library **Sastrawi**).
- **Collaborative berbobot:** kalikan skor tetangga dengan nilai kemiripannya, sehingga tetangga yang lebih mirip lebih berpengaruh.
- **Item-based CF** atau **Matrix Factorization (SVD/ALS)**, yang lebih tahan terhadap data sparse.
- **Tuning parameter:** uji jumlah tetangga (5/10/24), jumlah kandidat, dan bobot rating Hybrid, lalu pilih kombinasi terbaik berdasarkan hasil evaluasi (bagian A).

### C. Fitur aplikasi
- **Rekomendasi personal untuk pengguna web:** gunakan buku favorit sebagai riwayat, dan tampilkan "Rekomendasi untukmu" di Dashboard.
- **Onboarding cold start:** saat pertama mendaftar, pengguna memilih 3 genre favorit sebagai profil awal.
- **Rating & ulasan dari pengguna web** sebagai *explicit feedback* untuk memperkaya data.
- **Halaman statistik dataset** dengan grafik: genre terbanyak, sebaran rating, buku paling sering dipinjam.
- **Perintah latih ulang model** (misalnya `python manage.py train_model`) yang membuat ulang file `.pkl` dari data terbaru.

### D. Uji pengguna & deployment
- **Uji usability** dengan kuesioner **SUS (System Usability Scale)** atau survei kepuasan rekomendasi kepada beberapa responden.
- **Deploy online** (Render/Railway + PostgreSQL) agar bisa diakses penguji lewat tautan.

> Tips: pilih 1–2 saran (misalnya **A** dan perbaikan fitur Content-Based di **B**) lalu kerjakan sebelum sidang. Hasil evaluasi kuantitatif membuat presentasi jauh lebih kuat dibanding hanya demo aplikasi.

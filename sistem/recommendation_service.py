import pickle
import os
import pandas as pd
from django.conf import settings
from sistem.models import Book

# --- [BAGIAN 1] Logika untuk Rekomendasi Berdasarkan Kemiripan (TETAP ADA) ---
try:
    BOOKS_LIST_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'ml_model', 'books_list.pkl')
    SIMILARITY_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'ml_model', 'similarity.pkl')
    books_df_from_pkl = pickle.load(open(BOOKS_LIST_PATH, 'rb'))
    similarity_matrix = pickle.load(open(SIMILARITY_PATH, 'rb'))
    print("✅ Service: Model kemiripan (.pkl) berhasil dimuat.")
except Exception as e:
    print(f"❌ ERROR di service (pkl): {e}")
    books_df_from_pkl = None
    similarity_matrix = None

# --- [BAGIAN 2] Logika untuk Rekomendasi Berdasarkan Filter (BARU) ---
try:
    CSV_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'static', 'data',
                            'gabungan_buku.csv')  # Pastikan path CSV benar
    full_books_df = pd.read_csv(CSV_PATH, encoding='latin-1', on_bad_lines='skip')
    # Membersihkan data numerik
    full_books_df['rating'] = pd.to_numeric(full_books_df['rating'], errors='coerce')
    full_books_df['jml hlm'] = pd.to_numeric(full_books_df['jml hlm'], errors='coerce')
    full_books_df.dropna(subset=['rating', 'jml hlm', 'judul', 'penulis', 'genre'], inplace=True)
    print("✅ Service: DataFrame dari CSV untuk filter berhasil dimuat.")
except Exception as e:
    print(f"❌ ERROR di service (csv): {e}")
    full_books_df = None


# --- FUNGSI LAMA (TETAP ADA) ---
def get_recommendations(book_title: str, num_recommendations: int = 5):
    """
    Mengambil judul buku, mencari judul yang mirip, lalu mengambil objek buku lengkap
    dari database untuk judul-judul tersebut.
    """
    if books_df_from_pkl is None or similarity_matrix is None:
        return []

    try:
        book_index = books_df_from_pkl[books_df_from_pkl['judul'] == book_title].index[0]
        distances = sorted(list(enumerate(similarity_matrix[book_index])), reverse=True, key=lambda x: x[1])

        # Mengumpulkan HANYA judulnya terlebih dahulu
        recommended_titles = []
        for i in distances[1:num_recommendations + 1]:
            recommended_titles.append(books_df_from_pkl.iloc[i[0]].judul)

        # [PERBAIKAN] Ambil objek buku lengkap dari database berdasarkan daftar judul
        # Ini akan memberikan kita akses ke book.id, book.author, dll.
        recommended_books_qs = Book.objects.filter(title__in=recommended_titles)

        return recommended_books_qs

    except IndexError:
        return []
    except Exception as e:
        print(f"Error di get_recommendations: {e}")
        return []


# --- FUNGSI BARU ---
def get_filtered_recommendations(genre_preferensi=[], rating_min=0.0, halaman_maks=None, jumlah_rekomendasi=5):
    """
    Memberikan rekomendasi buku berdasarkan filter dari pengguna.
    Mengembalikan QuerySet objek Book dari database.
    """
    if full_books_df is None:
        return Book.objects.none()  # Kembalikan QuerySet kosong

    data_buku = full_books_df.copy()
    genre_preferensi = [genre.lower().strip() for genre in genre_preferensi]
    skor_buku = {}

    rekomendasi_final = Book.objects.none()

    for index, buku in data_buku.iterrows():
        skor = 0
        genre_buku_str = str(buku.get('genre', ''))
        genre_buku = [genre.lower().strip() for genre in genre_buku_str.split(',')]

        # Filter awal
        if buku['rating'] < rating_min:
            continue
        if halaman_maks is not None and buku['jml hlm'] > halaman_maks:
            continue

        if genre_preferensi and not any(g in genre_buku for g in genre_preferensi):
            continue

        # Skor
        skor += sum(1 for g in genre_preferensi if any(g in gb for gb in genre_buku))
        skor += 0.2 * buku['rating']

        skor_buku[index] = skor

    rekomendasi_terurut = sorted(skor_buku.items(), key=lambda x: x[1], reverse=True)

    top_indices = [idx for idx, _ in rekomendasi_terurut[:jumlah_rekomendasi]]

    if top_indices:
        # [PERBAIKAN KUNCI]
        # 1. Ambil HANYA judul buku dari DataFrame hasil pemfilteran
        recommended_titles = data_buku.loc[top_indices]['judul'].tolist()

        # 2. Gunakan daftar judul tersebut untuk mencari OBJEK BUKU ASLI di database
        #    Objek dari database ini memiliki .id, .author, .title, dll.
        rekomendasi_final = Book.objects.filter(title__in=recommended_titles)

    return rekomendasi_final
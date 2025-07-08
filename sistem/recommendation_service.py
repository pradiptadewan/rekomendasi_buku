import pickle
import os
import pandas as pd
from django.conf import settings
from .models import Book, Favorite
from django.db.models import Count

# --- 1. Memuat semua data dan model yang dibutuhkan ---
try:
    # Model untuk Content-Based
    BOOKS_LIST_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'ml_model', 'books_list.pkl')
    SIMILARITY_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'ml_model', 'similarity.pkl')
    books_df_from_pkl = pickle.load(open(BOOKS_LIST_PATH, 'rb'))
    similarity_matrix = pickle.load(open(SIMILARITY_PATH, 'rb'))
    # Data mentah untuk Collaborative & Filter
    CSV_PATH = os.path.join(settings.BASE_DIR, 'sistem', 'static', 'data', 'gabungan_buku.csv')
    full_books_df = pd.read_csv(CSV_PATH, encoding='latin-1', on_bad_lines='skip')


    full_books_df['rating'] = pd.to_numeric(full_books_df['rating'], errors='coerce')
    full_books_df['jml hlm'] = pd.to_numeric(full_books_df['jml hlm'], errors='coerce')
    full_books_df.dropna(subset=['rating', 'jml hlm', 'judul', 'penulis', 'genre', 'username'], inplace=True)

    # Matriks untuk Collaborative
    interaction_df = full_books_df[['username', 'judul', 'status']].drop_duplicates()
    status_map = {'Borrowing': 3, 'Borrowed': 2, 'Queue': 1}
    interaction_df['skor_interaksi'] = interaction_df['status'].map(status_map)
    user_item_matrix = interaction_df.pivot_table(index='username', columns='judul', values='skor_interaksi',
                                                  fill_value=0)

    from sklearn.metrics.pairwise import cosine_similarity

    user_similarity_df = pd.DataFrame(cosine_similarity(user_item_matrix), index=user_item_matrix.index,
                                      columns=user_item_matrix.index)
    print("✅ Service: Matriks kemiripan pengguna berhasil dibuat.")
except Exception as e:
    print(f"❌ ERROR saat memuat data di service: {e}")
    # Set semua ke None jika ada error
    books_df_from_pkl, similarity_matrix, full_books_df, user_item_matrix, user_similarity_df = [None] * 5


# --- [BAGIAN 2] FUNGSI-FUNGSI PEMBANTU ---

def _get_social_proof(source_book_title, recommended_book_obj):
    try:
        source_book_favorites = Favorite.objects.filter(book__title=source_book_title)
        users_who_liked_source = source_book_favorites.values_list('user_id', flat=True)
        total_likers_source = len(users_who_liked_source)
        if total_likers_source < 5:
            return None
        likers_who_also_liked_rec = Favorite.objects.filter(
            user_id__in=users_who_liked_source, book=recommended_book_obj
        ).count()
        if likers_who_also_liked_rec > 0:
            percentage = round((likers_who_also_liked_rec / total_likers_source) * 100)
            return f"{percentage}% pembaca '{source_book_title}' juga memfavoritkan buku ini."
    except Exception as e:
        print(f"Error di _get_social_proof: {e}")
    return None


def _get_feature_proof(source_book_obj, recommended_book_obj):
    try:
        source_genres = set(g.strip() for g in source_book_obj.genre.split(','))
        rec_genres = set(g.strip() for g in recommended_book_obj.genre.split(','))
        matching_genres = list(source_genres.intersection(rec_genres))
        if matching_genres:
            return {"text": "Berbagi beberapa genre yang sama:", "tags": matching_genres}
    except Exception as e:
        print(f"Error di _get_feature_proof: {e}")
    return None


# --- [BAGIAN 3] FUNGSI REKOMENDASI UTAMA ---

# FUNGSI 1: Berdasarkan Judul
def get_recommendations_with_strong_reasons(book_title: str, num_recommendations: int = 5):
    if books_df_from_pkl is None or similarity_matrix is None: return []
    try:
        source_book_obj = Book.objects.get(title=book_title)
    except Book.DoesNotExist:
        return []
    try:
        book_index = books_df_from_pkl[books_df_from_pkl['judul'] == book_title].index[0]
        distances = sorted(list(enumerate(similarity_matrix[book_index])), reverse=True, key=lambda x: x[1])
        recommended_titles = [books_df_from_pkl.iloc[i[0]].judul for i in distances[1:num_recommendations + 1]]
    except IndexError:
        return []

    recommended_books_qs = Book.objects.filter(title__in=recommended_titles)
    final_results = []
    for rec_book_obj in recommended_books_qs:
        details = {
            'social_proof': _get_social_proof(book_title, rec_book_obj),
            'feature_proof': _get_feature_proof(source_book_obj, rec_book_obj)
        }
        details = {k: v for k, v in details.items() if v is not None}
        main_reason = f"Karena Anda mencari '{source_book_obj.title}', buku ini mungkin relevan."
        if details.get('feature_proof'):
            main_reason = f"Memiliki kemiripan konten dengan '{source_book_obj.title}'."
        final_results.append({'book': rec_book_obj, 'main_reason': main_reason, 'details': details})
    return final_results


# FUNGSI 2: Berdasarkan Filter
def get_filtered_recommendations_with_strong_reasons(genre_preferensi=[], rating_min=0.0, halaman_maks=None,
                                                     jumlah_rekomendasi=10):
    if full_books_df is None: return []

    data_buku = full_books_df.copy()
    if rating_min > 0:
        data_buku = data_buku[data_buku['rating'] >= rating_min]
    if halaman_maks is not None:
        data_buku = data_buku[data_buku['jml hlm'] <= halaman_maks]
    if genre_preferensi:
        pattern = '|'.join([g.strip() for g in genre_preferensi])
        data_buku = data_buku[data_buku['genre'].str.contains(pattern, case=False, na=False)]
    if data_buku.empty: return []

    top_books_df = data_buku.sort_values(by='rating', ascending=False).head(jumlah_rekomendasi)
    recommended_titles = top_books_df['judul'].tolist()
    rekomendasi_qs = Book.objects.filter(title__in=recommended_titles)

    final_results = []
    for book in rekomendasi_qs:
        main_reason = "Dipilih berdasarkan kriteria filter yang Anda tentukan."
        details = {
            "feature_proof": {
                "text": "Sesuai dengan filter:",
                "tags": [f"Rating > {rating_min}"] + [f"Genre: {g.capitalize()}" for g in genre_preferensi]
            }
        }
        final_results.append({'book': book, 'main_reason': main_reason, 'details': details})
    return final_results


# Tambahkan ini di dalam file sistem/recommendation_service.py

# ... (kode dan import yang sudah ada di atasnya) ...

# Matriks interaksi pengguna-buku (dibuat sekali saat server jalan)
try:
    if full_books_df is not None:
        # Kita hanya butuh data interaksi unik
        interaction_df = full_books_df[['username', 'judul', 'status']].drop_duplicates()

        status_map = {'Borrowing': 3, 'Borrowed': 2, 'Queue': 1}
        interaction_df['skor_interaksi'] = interaction_df['status'].map(status_map)

        # Membuat matriks pivot
        user_item_matrix = interaction_df.pivot_table(index='username', columns='judul', values='skor_interaksi',
                                                      fill_value=0)

        # Menghitung kemiripan antar pengguna
        from sklearn.metrics.pairwise import cosine_similarity

        user_similarity = cosine_similarity(user_item_matrix)
        user_similarity_df = pd.DataFrame(user_similarity, index=user_item_matrix.index, columns=user_item_matrix.index)
        print("✅ Service: Matriks kemiripan pengguna untuk collaborative filtering berhasil dibuat.")
    else:
        user_item_matrix = None
        user_similarity_df = None
except Exception as e:
    print(f"❌ ERROR saat membuat matriks collaborative: {e}")
    user_item_matrix = None
    user_similarity_df = None


# [FUNGSI BARU 1] Untuk mencari riwayat buku
def get_user_history(username):
    if user_item_matrix is None or username not in user_item_matrix.index:
        return []

    # Ambil buku yang skornya lebih dari 0
    user_books = user_item_matrix.loc[username]
    history = user_books[user_books > 0].index.tolist()
    return history


# [FUNGSI BARU 2] Untuk rekomendasi collaborative
def get_collaborative_recommendations(username, top_n=5):
    if user_similarity_df is None or username not in user_similarity_df.index:
        return []

    # 1. Cari 5 pengguna lain yang paling mirip (tidak termasuk diri sendiri)
    similar_users = user_similarity_df[username].sort_values(ascending=False)[1:6]

    # 2. Ambil semua buku yang sudah dibaca oleh pengguna-pengguna mirip tersebut
    similar_users_books = user_item_matrix.loc[similar_users.index]

    # 3. Hitung skor rekomendasi (disederhanakan)
    recommendation_scores = similar_users_books.sum(axis=0)

    # 4. Hapus buku yang sudah pernah dipinjam oleh pengguna target
    user_history = get_user_history(username)
    recommendation_scores = recommendation_scores.drop(user_history, errors='ignore')

    # 5. Ambil N buku teratas
    top_books = recommendation_scores.sort_values(ascending=False).head(top_n).index.tolist()

    # Ambil detail buku dari database
    return Book.objects.filter(title__in=top_books)


def get_hybrid_recommendations(username, num_candidates=25, top_n=5):
    """
    Memberikan rekomendasi hybrid:
    1. Cari kandidat buku via Collaborative Filtering.
    2. Urutkan ulang kandidat berdasarkan kemiripan konten (genre) dengan riwayat pengguna.
    """
    if user_similarity_df is None or full_books_df is None or username not in user_similarity_df.index:
        return Book.objects.none()

    # --- TAHAP 1: MENCARI KANDIDAT (COLLABORATIVE) ---
    similar_users = user_similarity_df[username].sort_values(ascending=False)[1:num_candidates]
    similar_users_books = user_item_matrix.loc[similar_users.index]
    recommendation_scores = similar_users_books.sum(axis=0)
    user_history_titles = get_user_history(username)
    recommendation_scores = recommendation_scores.drop(user_history_titles, errors='ignore')

    # Ambil judul buku kandidat
    candidate_titles = recommendation_scores.sort_values(ascending=False).head(num_candidates).index.tolist()

    # --- TAHAP 2: MEMBUAT PROFIL KONTEN PENGGUNA ---
    # Cari genre apa yang paling sering dibaca oleh pengguna ini
    user_history_df = full_books_df[full_books_df['judul'].isin(user_history_titles)]
    user_genres = user_history_df['genre'].str.split(', ').explode().str.strip().value_counts()

    # Ambil 3 genre teratas
    top_user_genres = user_genres.head(3).index.tolist()

    # --- TAHAP 3: MEMBERI SKOR ULANG & MENGURUTKAN (CONTENT-BASED) ---
    final_scores = {}
    candidate_books_df = full_books_df[full_books_df['judul'].isin(candidate_titles)]

    for index, book in candidate_books_df.iterrows():
        score = 0
        book_genres_str = str(book.get('genre', ''))
        book_genres = [g.strip().lower() for g in book_genres_str.split(',')]

        # Tambah skor untuk setiap genre yang cocok dengan profil pengguna
        for user_genre in top_user_genres:
            if user_genre.lower() in book_genres:
                score += 1

        # Tambahkan skor rating sebagai bonus
        score += 0.2 * book['rating']
        final_scores[book['judul']] = score

    # Urutkan berdasarkan skor konten yang baru
    sorted_by_content = sorted(final_scores.items(), key=lambda item: item[1], reverse=True)

    # Ambil N judul teratas
    final_recommended_titles = [title for title, score in sorted_by_content[:top_n]]

    # Ambil objek buku lengkap dari database
    return Book.objects.filter(title__in=final_recommended_titles)



# EVALUATION

def evaluate_collaborative_detailed(username):
    """
    Memberikan laporan super detail tentang proses collaborative filtering.
    """
    if user_similarity_df is None or username not in user_similarity_df.index:
        return None

    # Langkah 1: Dapatkan riwayat buku dari pengguna target
    target_user_history = set(get_user_history(username))

    # Langkah 2: Dapatkan 5 pengguna paling mirip
    similar_users = user_similarity_df[username].sort_values(ascending=False)[1:6]

    evaluation_report = []
    # Langkah 3: Untuk setiap pengguna mirip, cari tahu kenapa mereka mirip
    for similar_user_name, similarity_score in similar_users.items():
        similar_user_history = set(get_user_history(similar_user_name))

        # Cari buku apa saja yang mereka baca BERSAMAAN
        common_books = list(target_user_history.intersection(similar_user_history))

        # Cari buku rekomendasi (buku yang dimiliki user mirip, tapi tidak oleh user target)
        new_recommendations = list(similar_user_history.difference(target_user_history))

        evaluation_report.append({
            'username': similar_user_name,
            'similarity_score': similarity_score,
            'common_books': common_books[:5],  # Tampilkan maks 5 buku
            'new_recommendations': new_recommendations[:3]  # Tampilkan maks 3 rekomendasi baru dari user ini
        })

    return evaluation_report


def evaluate_content_based_detailed(book_title):
    """
    Memberikan laporan perbandingan atribut yang sangat detail antara
    buku sumber dan buku-buku yang direkomendasikan.
    """
    if books_df_from_pkl is None or similarity_matrix is None or full_books_df is None:
        return None

    try:
        # --- Langkah 1: Ambil data buku sumber ---
        source_book_index = books_df_from_pkl[books_df_from_pkl['judul'] == book_title].index[0]
        # Ambil detail lengkap dari DataFrame CSV
        source_book_details = full_books_df[full_books_df['judul'] == book_title].iloc[0]
        source_genres = set([g.strip().lower() for g in str(source_book_details.get('genre', '')).split(',')])
        source_author = source_book_details.get('penulis', '').lower()

        # --- Langkah 2: Dapatkan buku-buku yang mirip ---
        distances = sorted(list(enumerate(similarity_matrix[source_book_index])), reverse=True, key=lambda x: x[1])

        evaluation_report = []
        for i in distances[1:6]:  # Ambil top 5
            recommended_book_title = books_df_from_pkl.iloc[i[0]].judul

            # Ambil detail lengkap buku rekomendasi dari DataFrame CSV
            rec_book_details = full_books_df[full_books_df['judul'] == recommended_book_title].iloc[0]
            rec_genres = set([g.strip().lower() for g in str(rec_book_details.get('genre', '')).split(',')])
            rec_author = rec_book_details.get('penulis', '').lower()

            # --- Langkah 3: Lakukan Perbandingan Detail ---
            matches = []
            # Bandingkan Penulis
            if rec_author == source_author:
                matches.append({'attribute': 'Author', 'value': rec_book_details.get('penulis')})

            # Bandingkan Genre
            common_genres = source_genres.intersection(rec_genres)
            if common_genres:
                matches.append({'attribute': 'Genre', 'value': ', '.join(g.title() for g in common_genres)})

            evaluation_report.append({
                'book_object': Book.objects.get(title=recommended_book_title),  # Kirim objek buku asli
                'similarity_score': i[1],
                'matches': matches  # Kirim daftar kecocokan
            })

        return evaluation_report
    except (IndexError, KeyError, Book.DoesNotExist) as e:
        print(f"Error pada evaluasi content-based: {e}")
        return None


# Tambahkan fungsi ini di bagian akhir file sistem/recommendation_service.py

def evaluate_hybrid_detailed(username, num_candidates=25):
    """
    Memberikan laporan detail tentang proses rekomendasi hybrid langkah demi langkah.
    """
    if user_similarity_df is None or full_books_df is None or username not in user_similarity_df.index:
        return None

    report = {}

    # --- TAHAP 1: PENCARIAN KANDIDAT (COLLABORATIVE) ---
    similar_users = user_similarity_df[username].sort_values(ascending=False)[1:num_candidates]
    similar_users_books = user_item_matrix.loc[similar_users.index]
    recommendation_scores = similar_users_books.sum(axis=0)
    user_history_titles = get_user_history(username)
    recommendation_scores = recommendation_scores.drop(user_history_titles, errors='ignore')
    candidate_titles = recommendation_scores.sort_values(ascending=False).head(num_candidates).index.tolist()

    report['stage1_candidates'] = {
        'count': len(candidate_titles),
        'books': candidate_titles
    }

    # --- TAHAP 2: PEMBUATAN PROFIL KONTEN PENGGUNA ---
    user_history_df = full_books_df[full_books_df['judul'].isin(user_history_titles)]
    user_genres = user_history_df['genre'].str.split(', ').explode().str.strip().value_counts()
    top_user_genres = user_genres.head(3).index.tolist()

    report['stage2_profile'] = {
        'top_genres': top_user_genres
    }

    # --- TAHAP 3: PENGURUTAN ULANG (CONTENT-BASED) ---
    final_scores = {}
    candidate_books_df = full_books_df[full_books_df['judul'].isin(candidate_titles)].copy()

    # Buat kolom baru untuk alasan re-ranking
    candidate_books_df['reasoning'] = ''

    for index, book in candidate_books_df.iterrows():
        score = 0
        matching_reasons = []
        book_genres_str = str(book.get('genre', ''))
        book_genres = [g.strip().lower() for g in book_genres_str.split(',')]

        for user_genre in top_user_genres:
            if user_genre.lower() in book_genres:
                score += 1
                matching_reasons.append(user_genre.title())

        score += 0.2 * book['rating']
        final_scores[book['judul']] = score

        # Simpan alasan kecocokan
        if matching_reasons:
            candidate_books_df.loc[index, 'reasoning'] = f"Cocok dengan genre: {', '.join(matching_reasons)}"
        else:
            candidate_books_df.loc[index, 'reasoning'] = "Skor dari rating & popularitas"

    # Tambahkan skor akhir ke DataFrame kandidat
    candidate_books_df['final_score'] = candidate_books_df['judul'].map(final_scores)

    # Urutkan berdasarkan skor akhir
    reranked_df = candidate_books_df.sort_values(by='final_score', ascending=False)

    report['stage3_reranked_books'] = reranked_df.head(10).to_dict('records')

    return report
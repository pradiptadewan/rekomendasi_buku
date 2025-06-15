import pandas as pd
from django.shortcuts import render
from sklearn.metrics.pairwise import cosine_similarity

# Load dan siapkan data hanya sekali
DATASET_PATH = 'sistem/static/data/gabungan_buku.csv'
df = pd.read_csv(DATASET_PATH)
df = df.drop_duplicates(['username', 'judul'])
df['genre'] = df['genre'].str.strip()
df_interaksi = df[['username', 'judul', 'status']]

# Map status ke skor
status_map = {'Borrowing': 3, 'Borrowed': 2, 'Queue': 1}
df_interaksi['skor_interaksi'] = df_interaksi['status'].map(status_map)

# Matriks interaksi pengguna-buku
matriks = df_interaksi.pivot_table(index='username', columns='judul', values='skor_interaksi', fill_value=0)
similaritas = cosine_similarity(matriks)
sim_df = pd.DataFrame(similaritas, index=matriks.index, columns=matriks.index)

# Fungsi rekomendasi pengguna lama
def recommend_books(username, top_n=5):
    if username not in sim_df:
        return []
    similar_users = sim_df[username].sort_values(ascending=False)[1:6]
    weighted_scores = matriks.loc[similar_users.index].T.dot(similar_users)
    user_books = set(matriks.loc[username][matriks.loc[username] > 0].index)
    rekomendasi = weighted_scores[~weighted_scores.index.isin(user_books)].sort_values(ascending=False).head(top_n)
    return rekomendasi.index.tolist()

# Fungsi rekomendasi pengguna baru (berdasarkan popularitas global)
def recommend_new_user(top_n=5):
    popular_books = df['judul'].value_counts().head(top_n).index.tolist()
    return popular_books

# Fungsi riwayat buku
def get_user_history(username):
    if username in matriks.index:
        return matriks.loc[username][matriks.loc[username] > 0].index.tolist()
    return []

# Tampilan awal

def index(request):
    return render(request, 'sistem/index.html')

# Proses rekomendasi
def recommend(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        if username in matriks.index:
            hasil = recommend_books(username)
            riwayat = get_user_history(username)
        else:
            hasil = recommend_new_user()
            riwayat = []
        return render(request, 'sistem/index.html', {
            'username': username,
            'hasil': hasil,
            'riwayat': riwayat,
            'baru': username not in matriks.index
        })
    return render(request, 'sistem/index.html')
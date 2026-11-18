"""
Logika sistem rekomendasi: Content-Based, Collaborative, dan Hybrid.

Data (CSV + model .pkl) dimuat sekali saat pertama kali dibutuhkan, lalu disimpan di memori.
"""
import logging
import pickle
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from .genres import parse_genres
from .models import Book, Favorite

logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).resolve().parent
CSV_PATH = APP_DIR / 'data' / 'gabungan_buku.csv'
BOOKS_PKL_PATH = APP_DIR / 'ml_model' / 'books_list.pkl'
SIMILARITY_PKL_PATH = APP_DIR / 'ml_model' / 'similarity.pkl'

# Skor interaksi pembaca terhadap buku, berdasarkan status peminjaman.
STATUS_SCORES = {'borrowing': 3, 'borrowed': 2, 'queue': 1}
STATUS_LABELS = {3: 'Sedang dipinjam', 2: 'Sudah dipinjam', 1: 'Dalam antrean'}
# Salah ketik status yang ada di dataset.
STATUS_TYPOS = {'borrowes': 'borrowed', 'boorowed': 'borrowed', 'borrowd': 'borrowed', 'borrowied': 'borrowed'}

COLLABORATIVE_NEIGHBORS = 5
HYBRID_NEIGHBORS = 24
HYBRID_CANDIDATES = 25
HYBRID_TOP_GENRES = 3
HYBRID_RATING_WEIGHT = 0.2
SOCIAL_PROOF_MIN_LIKERS = 5


def load_dataset(path=CSV_PATH):
    """Baca CSV peminjaman dan rapikan kolomnya. Satu baris = satu interaksi pembaca dengan buku."""
    df = pd.read_csv(path, encoding='utf-8', encoding_errors='replace', on_bad_lines='skip')
    df = df.dropna(subset=['judul', 'penulis'])
    df['rating'] = pd.to_numeric(df['rating'], errors='coerce')
    df['jml hlm'] = pd.to_numeric(df['jml hlm'], errors='coerce')
    status = df['status'].fillna('').astype(str).str.strip().str.lower().replace(STATUS_TYPOS)
    df['skor'] = status.map(STATUS_SCORES)
    return df


@dataclass(frozen=True)
class RecommenderData:
    titles: list            # judul sesuai urutan baris/kolom matriks kemiripan konten
    positions: dict         # judul -> nomor baris di matriks kemiripan konten
    content_similarity: np.ndarray
    books: pd.DataFrame     # satu baris per judul (index = judul)
    user_item: pd.DataFrame     # pembaca x judul, isinya skor interaksi
    user_similarity: pd.DataFrame


@lru_cache(maxsize=1)
def get_data():
    try:
        with open(BOOKS_PKL_PATH, 'rb') as f:
            books_pkl = pickle.load(f)
        with open(SIMILARITY_PKL_PATH, 'rb') as f:
            content_similarity = pickle.load(f)

        # Index DataFrame di .pkl bukan 0..n-1, jadi pakai urutan posisi, bukan label index.
        titles = books_pkl['judul'].tolist()
        if content_similarity.shape != (len(titles), len(titles)):
            raise ValueError('Ukuran similarity.pkl tidak sesuai dengan books_list.pkl')

        df = load_dataset()
        books = df.drop_duplicates('judul').set_index('judul')[['penulis', 'rating', 'jml hlm', 'genre']]
        books['genres'] = books['genre'].map(parse_genres)

        interactions = (
            df.dropna(subset=['username', 'skor'])
            .groupby(['username', 'judul'])['skor'].max()
        )
        user_item = interactions.unstack(fill_value=0)
        # errstate: BLAS bawaan macOS memberi RuntimeWarning palsu pada matmul; hasilnya tetap benar.
        with np.errstate(all='ignore'):
            similarity = cosine_similarity(user_item.values)
        user_similarity = pd.DataFrame(similarity, index=user_item.index, columns=user_item.index)
    except Exception:
        logger.exception('Gagal memuat data sistem rekomendasi')
        return None

    logger.info('Data rekomendasi dimuat: %d buku, %d pembaca', len(books), len(user_item))
    return RecommenderData(
        titles=titles,
        positions={title: i for i, title in enumerate(titles)},
        content_similarity=content_similarity,
        books=books,
        user_item=user_item,
        user_similarity=user_similarity,
    )


# ---------------------------------------------------------------------------
# Fungsi bantu
# ---------------------------------------------------------------------------

def _books_in_order(titles):
    """Ambil objek Book dari database dengan urutan yang sama seperti `titles`."""
    found = Book.objects.in_bulk(list(titles), field_name='title')
    return [found[t] for t in titles if t in found]


def _rating(data, title):
    rating = data.books.at[title, 'rating']
    return 0.0 if pd.isna(rating) else float(rating)


def _genre_overlap(a, b):
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def _neighbors(data, username, k):
    """k pembaca paling mirip (selain dirinya sendiri) yang skor kemiripannya > 0."""
    sims = data.user_similarity.loc[username].drop(username)
    sims = sims[sims > 0]
    return sims.sort_values(ascending=False, kind='mergesort').head(k)


def _read_titles(data, username):
    row = data.user_item.loc[username]
    return row[row > 0]


def _candidate_scores(data, username, neighbors):
    """Jumlah skor interaksi para tetangga untuk buku yang belum dibaca pembaca target."""
    if neighbors.empty:
        return pd.Series(dtype=float)
    scores = data.user_item.loc[neighbors.index].sum(axis=0)
    scores = scores.drop(_read_titles(data, username).index)
    return scores[scores > 0].sort_values(ascending=False, kind='mergesort')


def _has_user(data, username):
    return data is not None and username in data.user_item.index


# ---------------------------------------------------------------------------
# Data untuk form
# ---------------------------------------------------------------------------

def dataset_users():
    data = get_data()
    return data.user_item.index.tolist() if data else []


def dataset_titles():
    data = get_data()
    return sorted(data.titles, key=str.lower) if data else []


def popular_genres(limit=12):
    data = get_data()
    if not data:
        return []
    counts = Counter(g for genres in data.books['genres'] for g in genres)
    return [genre for genre, _ in counts.most_common(limit)]


def dataset_stats():
    data = get_data()
    if not data:
        return None
    genres = {g for genres in data.books['genres'] for g in genres}
    return {'books': len(data.books), 'readers': len(data.user_item), 'genres': len(genres)}


def user_history(username):
    """Riwayat pinjam pembaca dataset, diurutkan dari interaksi terkuat."""
    data = get_data()
    if not _has_user(data, username):
        return []
    read = _read_titles(data, username).sort_values(ascending=False, kind='mergesort')
    return [{'title': title, 'status': STATUS_LABELS.get(int(score), '')} for title, score in read.items()]


# ---------------------------------------------------------------------------
# Content-Based Filtering
# ---------------------------------------------------------------------------

def content_based(title, n=5):
    """
    Buku paling mirip dengan `title` menurut matriks kemiripan konten (similarity.pkl).
    Jika skor kemiripan sama (termasuk 0), urutan ditentukan oleh kesamaan genre lalu rating.
    """
    data = get_data()
    if not data or title not in data.positions:
        return []

    pos = data.positions[title]
    source_genres = data.books.at[title, 'genres']
    source_author = str(data.books.at[title, 'penulis']).strip().lower()

    ranked = []
    for i, score in enumerate(data.content_similarity[pos]):
        other = data.titles[i]
        if i == pos or other not in data.books.index:
            continue
        overlap = _genre_overlap(source_genres, data.books.at[other, 'genres'])
        ranked.append((-float(score), -overlap, -_rating(data, other), other))
    ranked.sort()
    top = ranked[:n]

    books = {b.title: b for b in _books_in_order([t for *_, t in top])}
    likers = list(Favorite.objects.filter(book__title=title).values_list('user_id', flat=True))

    items = []
    for neg_score, _, _, other in top:
        if other not in books:
            continue
        book = books[other]
        shared_genres = [g for g in source_genres if g in data.books.at[other, 'genres']]
        same_author = str(data.books.at[other, 'penulis']).strip().lower() == source_author

        if same_author:
            reason = 'Ditulis oleh penulis yang sama.'
        elif -neg_score > 0:
            reason = 'Judul atau penulisnya mirip.'
        elif shared_genres:
            reason = 'Memiliki genre yang sama.'
        else:
            reason = 'Pilihan dengan rating tinggi.'

        social_proof = None
        if len(likers) >= SOCIAL_PROOF_MIN_LIKERS:
            also_liked = Favorite.objects.filter(user_id__in=likers, book=book).count()
            if also_liked:
                social_proof = f'{round(also_liked / len(likers) * 100)}% penyuka buku ini juga memfavoritkannya.'

        items.append({
            'book': book,
            'score': -neg_score,
            'shared_genres': shared_genres,
            'tags': shared_genres,
            'same_author': same_author,
            'reason': reason,
            'social_proof': social_proof,
        })
    return items


def filter_books(genres=(), rating_min=None, max_pages=None, n=10):
    """Buku yang memenuhi filter. Genre dicocokkan secara utuh (memilih "fiksi" tidak ikut "nonfiksi")."""
    data = get_data()
    if not data:
        return []
    wanted = [g.lower() for g in genres]

    ranked = []
    for title, row in data.books.iterrows():
        rating = row['rating']
        pages = row['jml hlm']
        if rating_min is not None and (pd.isna(rating) or rating < rating_min):
            continue
        if max_pages is not None and (pd.isna(pages) or pages > max_pages):
            continue
        matched = [g for g in wanted if g in row['genres']]
        if wanted and not matched:
            continue
        ranked.append((-len(matched), -_rating(data, title), title, matched))
    ranked.sort(key=lambda r: r[:3])
    top = ranked[:n]

    books = {b.title: b for b in _books_in_order([r[2] for r in top])}
    items = []
    for _, _, title, matched in top:
        if title not in books:
            continue
        tags = [g.title() for g in matched]
        if rating_min is not None:
            tags.append(f'Rating ≥ {rating_min:g}')
        if max_pages is not None:
            tags.append(f'≤ {max_pages} halaman')
        items.append({'book': books[title], 'reason': 'Sesuai filter: ' + ', '.join(tags) if tags else None})
    return items


# ---------------------------------------------------------------------------
# Collaborative Filtering
# ---------------------------------------------------------------------------

def collaborative(username, n=5):
    data = get_data()
    if not _has_user(data, username):
        return []
    neighbors = _neighbors(data, username, COLLABORATIVE_NEIGHBORS)
    scores = _candidate_scores(data, username, neighbors).head(n)
    neighbor_rows = data.user_item.loc[neighbors.index]

    items = []
    for book in _books_in_order(scores.index):
        readers = int((neighbor_rows[book.title] > 0).sum())
        items.append({
            'book': book,
            'score': float(scores[book.title]),
            'reason': f'Dibaca {readers} dari {len(neighbors)} pembaca dengan selera serupa.',
        })
    return items


def evaluate_collaborative(username):
    data = get_data()
    if not _has_user(data, username):
        return None
    history = set(_read_titles(data, username).index)
    neighbors = []
    for name, similarity in _neighbors(data, username, COLLABORATIVE_NEIGHBORS).items():
        their_books = set(_read_titles(data, name).index)
        neighbors.append({
            'username': name,
            'similarity': float(similarity),
            'common_books': sorted(history & their_books, key=str.lower),
            'new_books': sorted(their_books - history, key=str.lower),
        })
    return {
        'history': user_history(username),
        'neighbors': neighbors,
        'recommendations': collaborative(username),
    }


# ---------------------------------------------------------------------------
# Hybrid: kandidat dari Collaborative, lalu diurutkan ulang dengan profil genre (Content-Based)
# ---------------------------------------------------------------------------

def hybrid_report(username, n=5, show=10):
    data = get_data()
    if not _has_user(data, username):
        return None

    neighbors = _neighbors(data, username, HYBRID_NEIGHBORS)
    candidates = _candidate_scores(data, username, neighbors).head(HYBRID_CANDIDATES)

    # Profil genre dihitung dari buku unik yang pernah dipinjam pembaca ini.
    history = _read_titles(data, username).sort_values(ascending=False, kind='mergesort')
    genre_counts = Counter(g for title in history.index for g in data.books.at[title, 'genres'])
    top_genres = [g for g, _ in genre_counts.most_common(HYBRID_TOP_GENRES)]

    ranked = []
    for title, collab_score in candidates.items():
        matched = [g for g in top_genres if g in data.books.at[title, 'genres']]
        rating = _rating(data, title)
        score = len(matched) + HYBRID_RATING_WEIGHT * rating
        ranked.append({
            'title': title,
            'score': score,
            'collab_score': float(collab_score),
            'rating': rating,
            'matched_genres': matched,
            'tags': matched,
            'reason': (
                f"Cocok dengan genre favorit: {', '.join(g.title() for g in matched)}."
                if matched else 'Tidak ada genre yang cocok; skor hanya dari rating.'
            ),
        })
    ranked.sort(key=lambda r: (-r['score'], -r['collab_score'], r['title']))

    shown = ranked[:max(n, show)]
    books = {b.title: b for b in _books_in_order([r['title'] for r in shown])}
    for row in shown:
        row['book'] = books.get(row['title'])

    return {
        'neighbor_count': len(neighbors),
        'candidates': [{'title': t, 'score': float(s)} for t, s in candidates.items()],
        'top_genres': top_genres,
        'ranked': [r for r in shown[:show] if r['book']],
        'recommendations': [r for r in shown[:n] if r['book']],
    }


def hybrid(username, n=5):
    report = hybrid_report(username, n=n)
    return report['recommendations'] if report else []

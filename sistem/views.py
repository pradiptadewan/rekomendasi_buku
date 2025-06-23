import pandas as pd
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from sklearn.metrics.pairwise import cosine_similarity
from .forms import CustomUserCreationForm
from .models import Book, Favorite
from .recommendation_service import get_recommendations, full_books_df
from .recommendation_service import get_filtered_recommendations

DATASET_PATH = 'sistem/static/data/gabungan_buku.csv'

try:
    df = pd.read_csv(DATASET_PATH)
    df = df.drop_duplicates(['username', 'judul']).copy()  # Gunakan .copy() setelah drop_duplicates
    df['genre'] = df['genre'].str.strip()
    df_interaksi = df[['username', 'judul', 'status']].copy()  # Gunakan .copy() di sini juga
except FileNotFoundError:
    # Handle the case where the file is not found gracefully
    print(f"Error: Dataset file not found at {DATASET_PATH}. Please check the path.")
    # In a real application, you might want to log this error and display a user-friendly message
    df = pd.DataFrame()  # Create empty DataFrame to prevent further errors
    df_interaksi = pd.DataFrame()  # Create empty DataFrame

# Map status ke skor
status_map = {'Borrowing': 3, 'Borrowed': 2, 'Queue': 1}

# --- PERBAIKAN DI SINI UNTUK MENGHINDARI SettingWithCopyWarning ---
# Gunakan .loc untuk menetapkan kolom baru
if not df_interaksi.empty:
    df_interaksi.loc[:, 'skor_interaksi'] = df_interaksi['status'].map(status_map)

# Matriks interaksi pengguna-buku
matriks = pd.DataFrame()  # Initialize as empty
similaritas = None
sim_df = pd.DataFrame()

if not df_interaksi.empty:
    matriks = df_interaksi.pivot_table(index='username', columns='judul', values='skor_interaksi', fill_value=0)
    if not matriks.empty:  # Check if matriks is not empty before calculating similarity
        similaritas = cosine_similarity(matriks)
        sim_df = pd.DataFrame(similaritas, index=matriks.index, columns=matriks.index)


# Fungsi rekomendasi pengguna lama
def recommend_books(username, top_n=5):
    if username not in sim_df.index:  # Pastikan username ada di index sim_df, bukan hanya di sim_df
        return []
    # Mengatasi potensi kesalahan jika tidak ada pengguna lain yang mirip atau matriks kosong
    if sim_df.empty or username not in sim_df.columns:
        return []

    similar_users = sim_df[username].sort_values(ascending=False)[1:6]
    # Filter out users with 0 similarity (if any)
    similar_users = similar_users[similar_users > 0]

    if similar_users.empty or matriks.loc[similar_users.index].empty:
        return []

    weighted_scores = matriks.loc[similar_users.index].T.dot(similar_users)
    user_books = set(matriks.loc[username][matriks.loc[username] > 0].index)

    # Pastikan weighted_scores tidak kosong sebelum mencoba menyaring
    if weighted_scores.empty:
        return []

    rekomendasi = weighted_scores[~weighted_scores.index.isin(user_books)].sort_values(ascending=False).head(top_n)
    return rekomendasi.index.tolist()


# Fungsi rekomendasi pengguna baru (berdasarkan popularitas global)
def recommend_new_user(top_n=5):
    if not df.empty:
        popular_books = df['judul'].value_counts().head(top_n).index.tolist()
        return popular_books
    return []  # Return empty list if df is empty


# Fungsi riwayat buku
def get_user_history(username):
    if not matriks.empty and username in matriks.index:
        return matriks.loc[username][matriks.loc[username] > 0].index.tolist()
    return []


# Proses rekomendasi
def recommend(request):
    # Siapkan variabel kosong untuk menampung hasil
    recommendation_list = []
    book_title_searched = ""

    # Jika pengunjung menekan tombol "SUBMIT" di form (metodenya POST)
    if request.method == 'POST':
        # 1. Pramuniaga mengambil judul buku yang diketik pengunjung dari form
        # .strip() untuk menghapus spasi yang tidak sengaja terketik
        book_title_searched = request.POST.get('book_title', '').strip()

        # Pastikan pengunjung benar-benar mengetik sesuatu
        if book_title_searched:

            # 2. Pramuniaga bertanya ke Pustakawan Ahli dengan judul buku tersebut
            print(f"VIEW: Mencari rekomendasi untuk '{book_title_searched}'") # Ini untuk cek di terminal
            recommendation_list = get_recommendations(book_title=book_title_searched)
            print(f"VIEW: Hasil diterima: {recommendation_list}") # Cek hasil di terminal

    # 3. Pramuniaga menyiapkan data untuk ditampilkan di "etalase" (template)
    context = {
        'recommendations': recommendation_list,
        'searched_title': book_title_searched,
    }

    # Pramuniaga menampilkan hasilnya di halaman output.html
    return render(request, 'sistem/output.html', context)


def filter_input_view(request):
    """Menampilkan halaman form filter."""
    # Ambil beberapa genre unik dari DataFrame untuk ditampilkan sebagai pilihan
    # Ini sebaiknya di-cache agar tidak berjalan setiap saat
    if full_books_df is not None:
        all_genres = full_books_df['genre'].dropna().unique()
        # Ambil beberapa contoh genre populer
        sample_genres = ['Fiksi', 'Romansa', 'Fantasi', 'Misteri', 'Sains Fiksi', 'Horor', 'Biografi', 'Sejarah']
    else:
        sample_genres = []

    context = {'available_genres': sample_genres}
    return render(request, 'sistem/filter_input.html', context)


def filter_results_view(request):
    """Memproses form filter dan menampilkan hasilnya."""
    if request.method == 'POST':
        # Ambil semua genre yang dicentang
        genres = request.POST.getlist('genres')

        # Ambil dan proses input rating
        rating_str = request.POST.get('rating_min', '0')
        rating_min = float(rating_str) if rating_str else 0.0

        # Ambil dan proses input halaman
        halaman_str = request.POST.get('halaman_maks')
        halaman_maks = int(halaman_str) if halaman_str else None

        # Panggil service dengan filter dari pengguna
        recommendation_list = get_filtered_recommendations(
            genre_preferensi=genres,
            rating_min=rating_min,
            halaman_maks=halaman_maks
        )

        context = {'recommendations': recommendation_list}
        return render(request, 'sistem/filter_output.html', context)

    # Jika bukan POST, arahkan kembali ke halaman input
    return redirect('sistem:filter_input')


# --- Views Utama ---
def home(request):
    return render(request, 'sistem/home.html')


# --- Views Autentikasi ---
def register_view(request):
    if request.user.is_authenticated:
        return redirect('sistem:dashboard_user')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Cukup panggil save(), email sudah ditangani oleh form
            username = form.cleaned_data.get('username')
            messages.success(request, f'Akun untuk {username} berhasil dibuat. Silakan login.')
            return redirect('sistem:login')
        else:
            # Pesan error akan otomatis ditangani oleh rendering form di template
            pass
    else:
        form = CustomUserCreationForm()

    return render(request, 'sistem/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('sistem:dashboard_user')

    if request.method == 'POST':
        username_input = request.POST.get('username_email')
        password_input = request.POST.get('password')

        if not username_input or not password_input:
            messages.error(request, 'Username dan Password tidak boleh kosong.')
            return render(request, 'sistem/login.html')

        user = authenticate(request, username=username_input, password=password_input)

        if user is not None:
            # [PERBAIKAN "INGAT SAYA"]
            # Cek apakah checkbox 'remember_me' dicentang atau tidak
            if not request.POST.get('remember_me', None):
                # Jika TIDAK dicentang, sesi akan berakhir saat browser ditutup
                request.session.set_expiry(0)
            else:
                # Jika DICENTANG, sesi akan mengikuti durasi default Django (biasanya 2 minggu)
                # Kita tidak perlu melakukan apa-apa, ini adalah perilaku default.
                pass

            login(request, user)
            return redirect('sistem:dashboard_user')
        else:
            messages.error(request, 'Username atau Password salah.')
            return render(request, 'sistem/login.html')

    return render(request, 'sistem/login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah berhasil logout.')
    return redirect('sistem:login')


# --- Views Lainnya ---
def input_view(request):
    # View ini untuk menampilkan form input rekomendasi
    return render(request, 'sistem/input.html')


@login_required  # Lindungi view ini agar hanya user terautentikasi yang bisa akses
def output_view(request):
    return render(request, 'sistem/output.html')


def book_detail_view(request, book_id):
    """Menampilkan halaman detail untuk satu buku spesifik."""
    # Ambil satu objek buku berdasarkan ID-nya. Jika tidak ada, tampilkan error 404.
    book = get_object_or_404(Book, id=book_id)

    context = {
        'book': book
    }
    return render(request, 'sistem/details.html', context)


def dashboard_admin(request):
    # Pertama, cek apakah ada pengguna yang sudah login mencoba mengakses halaman ini
    if request.user.is_authenticated:
        # Jika ya, langsung arahkan ke dashboard pribadi mereka
        return redirect('sistem:dashboard_user')

    # Logikanya sekarang hampir sama dengan dashboard_user
    query = request.GET.get('q')

    if query:
        # Jika ada pencarian, filter buku
        books_to_display = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).distinct()
    else:
        # Jika tidak ada pencarian, tampilkan 8 buku terpopuler
        books_to_display = Book.objects.annotate(
            num_favorites=Count('favorite')
        ).order_by('-num_favorites')[:8]

    context = {
        'books': books_to_display,
        'search_query': query,
    }
    return render(request, 'sistem/dashboard.html', context)


@login_required
def dashboard_user(request):
    # Ambil kata kunci pencarian dari URL, jika ada
    query = request.GET.get('q')

    # Logika IF/ELSE baru:
    if query:
        # JIKA ADA PENCARIAN, jalankan logika filter
        # .distinct() untuk memastikan tidak ada hasil duplikat
        books_to_display = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).distinct()
    else:
        # JIKA TIDAK ADA PENCARIAN, tampilkan 8 buku terpopuler
        # 1. Hitung berapa kali setiap buku difavoritkan (annotate)
        # 2. Urutkan dari yang paling banyak favoritnya (order_by)
        # 3. Ambil 8 buku teratas (slicing)
        books_to_display = Book.objects.annotate(
            num_favorites=Count('favorite')
        ).order_by('-num_favorites')[:8]

    # Siapkan data untuk dikirim ke template
    context = {
        'books': books_to_display,  # Nama variabel tetap 'books'
        'search_query': query,
    }
    return render(request, 'sistem/dashboard_user.html', context)


@login_required
def add_to_favorite(request, book_id):
    """Fungsi untuk memproses saat tombol 'Add to Favorite' diklik."""
    book = get_object_or_404(Book, id=book_id)
    # Membuat entri favorit, jika sudah ada tidak akan dibuat duplikat
    favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)

    if created:
        messages.success(request, f"'{book.title}' telah ditambahkan ke favorit Anda!")
    else:
        messages.info(request, f"'{book.title}' sudah ada di daftar favorit Anda.")

    # Kembali ke halaman dashboard
    return redirect('sistem:dashboard_user')


@login_required
def favorite_list(request):
    """Fungsi untuk menampilkan halaman daftar favorit."""
    favorite_books = Book.objects.filter(favorite__user=request.user)

    context = {
        'favorite_books': favorite_books
    }
    return render(request, 'sistem/favorite.html', context)


@login_required
def remove_from_favorite(request, book_id):
    """Fungsi untuk menghapus buku dari daftar favorit pengguna."""
    # 1. Cari buku yang ingin dihapus berdasarkan ID-nya
    book = get_object_or_404(Book, id=book_id)

    # 2. Cari entri 'Favorite' yang menghubungkan pengguna ini dengan buku ini
    favorite_entry = Favorite.objects.filter(user=request.user, book=book)

    # 3. Jika entri tersebut ada, hapus
    if favorite_entry.exists():
        favorite_entry.delete()
        messages.success(request, f"'{book.title}' telah dihapus dari favorit Anda.")

    # 4. Arahkan pengguna kembali ke halaman daftar favorit
    return redirect('sistem:favorite_list')


@login_required
def all_popular_books_view(request):
    # 1. Ambil SEMUA buku, diurutkan berdasarkan yang paling populer
    all_books_list = Book.objects.annotate(
        num_favorites=Count('favorite')
    ).order_by('-num_favorites')

    # 2. Siapkan Paginator, tampilkan 12 buku per halaman
    paginator = Paginator(all_books_list, 12)

    # 3. Ambil nomor halaman dari URL (misal: /books/popular/?page=2)
    page_number = request.GET.get('page')

    # 4. Ambil objek halaman yang sesuai
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj  # Kirim objek halaman ke template
    }

    return render(request, 'sistem/all_popular_books.html', context)
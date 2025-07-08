import pandas as pd
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .recommendation_service import get_filtered_recommendations_with_strong_reasons, books_df_from_pkl, \
    evaluate_content_based_detailed, evaluate_collaborative_detailed, evaluate_hybrid_detailed
from .recommendation_service import get_user_history, get_collaborative_recommendations, user_item_matrix
from .recommendation_service import full_books_df
from .recommendation_service import get_hybrid_recommendations # Tambahkan ini di import
from .forms import CustomUserCreationForm
from .models import Book, Favorite
from .recommendation_service import get_recommendations_with_strong_reasons


def home(request):
    return render(request, 'sistem/home.html')

def input_view(request):
    return render(request, 'sistem/input.html')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('sistem:dashboard_user')
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Akun untuk {username} berhasil dibuat. Silakan login.')
            return redirect('sistem:login')
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
            if not request.POST.get('remember_me', None):
                request.session.set_expiry(0)
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

@login_required
def dashboard_user(request):
    query = request.GET.get('q')
    if query:
        books_to_display = Book.objects.filter(
            Q(title__icontains=query) | Q(author__icontains=query)
        ).distinct()
    else:
        books_to_display = Book.objects.annotate(
            num_favorites=Count('favorite')
        ).order_by('-num_favorites')[:8]
    context = {
        'books': books_to_display,
        'search_query': query,
    }
    return render(request, 'sistem/dashboard_user.html', context)

def book_detail_view(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    context = {'book': book}
    return render(request, 'sistem/details.html', context)

@login_required
def add_to_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if created:
        messages.success(request, f"'{book.title}' telah ditambahkan ke favorit Anda!")
    else:
        messages.info(request, f"'{book.title}' sudah ada di daftar favorit Anda.")
    return redirect('sistem:dashboard_user')

@login_required
def favorite_list(request):
    favorite_books = Book.objects.filter(favorite__user=request.user)
    context = {'favorite_books': favorite_books}
    return render(request, 'sistem/favorite.html', context)

@login_required
def remove_from_favorite(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    favorite_entry = Favorite.objects.filter(user=request.user, book=book)
    if favorite_entry.exists():
        favorite_entry.delete()
        messages.success(request, f"'{book.title}' telah dihapus dari favorit Anda.")
    return redirect('sistem:favorite_list')

@login_required
def all_popular_books_view(request):
    all_books_list = Book.objects.annotate(
        num_favorites=Count('favorite')
    ).order_by('-num_favorites')
    paginator = Paginator(all_books_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}
    return render(request, 'sistem/all_popular_books.html', context)

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


def collaborative_view(request):
    # Ambil semua username unik untuk dropdown
    all_users = user_item_matrix.index.tolist() if user_item_matrix is not None else []

    # Siapkan variabel untuk hasil
    selected_user = None
    history = []
    recommendations = []

    if request.method == 'POST':
        # Ambil username yang dipilih dari form
        selected_user = request.POST.get('username')
        if selected_user:
            # Panggil service untuk mendapatkan riwayat dan rekomendasi
            history = get_user_history(selected_user)
            recommendations = get_collaborative_recommendations(selected_user)

    context = {
        'all_users': all_users,
        'selected_user': selected_user,
        'history': history,
        'recommendations': recommendations
    }
    return render(request, 'sistem/collaborative.html', context)


def content_based_view(request):
    """
    Menangani halaman input dan output untuk Content-Based Filtering.
    Menampilkan form dan hasil di halaman yang sama.
    """
    # Data yang selalu dibutuhkan untuk mengisi form
    popular_genres = []
    all_titles = []
    if full_books_df is not None:
        all_genres = full_books_df['genre'].dropna().str.split(', ').explode().str.strip().unique()
        popular_genres = sorted([g for g in all_genres if len(g) > 2])[:12]
        all_titles = sorted(full_books_df['judul'].unique().tolist())

    # Inisialisasi variabel konteks untuk hasil
    context = {
        'available_genres': popular_genres,
        'all_book_titles': all_titles,
        'recommendation_items': None,  # Gunakan None agar template bisa cek
        'searched_title': None,
        'user_filters': None,
    }

    if request.method == 'POST':
        # Cek form mana yang di-submit berdasarkan nama tombol submit

        # --- Form 1: Pencarian Berdasarkan Judul ---
        if 'search_by_title' in request.POST:
            book_title_searched = request.POST.get('book_title', '').strip()
            if book_title_searched:
                recommendation_list = get_recommendations_with_strong_reasons(
                    book_title=book_title_searched
                )
                context['recommendation_items'] = recommendation_list
                context['searched_title'] = book_title_searched

        # --- Form 2: Pencarian Berdasarkan Filter ---
        elif 'search_by_filter' in request.POST:
            genres = request.POST.getlist('genres')
            rating_str = request.POST.get('rating_min', '0')
            rating_min = float(rating_str) if rating_str else 0.0
            halaman_str = request.POST.get('halaman_maks')
            halaman_maks = int(halaman_str) if halaman_str else None

            recommendation_list = get_filtered_recommendations_with_strong_reasons(
                genre_preferensi=genres,
                rating_min=rating_min,
                halaman_maks=halaman_maks
            )
            context['recommendation_items'] = recommendation_list
            context['user_filters'] = {'genres': genres, 'rating': rating_min, 'pages': halaman_maks}

    # Render template yang sama untuk GET dan POST
    # Contex akan berisi data form dan juga data hasil (jika ada)
    return render(request, 'sistem/content_based.html', context)


def hybrid_view(request):
    all_users = user_item_matrix.index.tolist() if user_item_matrix is not None else []

    selected_user = None
    recommendations = []

    if request.method == 'POST':
        selected_user = request.POST.get('username')
        if selected_user:
            # Panggil service hybrid yang baru
            recommendations = get_hybrid_recommendations(selected_user)

    context = {
        'all_users': all_users,
        'selected_user': selected_user,
        'recommendations': recommendations
    }
    return render(request, 'sistem/hybrid.html', context)


# Ganti fungsi evaluation_view yang lama dengan ini

def evaluation_view(request):
    # Pastikan variabel global dari service bisa diakses
    from .recommendation_service import user_item_matrix, books_df_from_pkl

    all_users = user_item_matrix.index.tolist() if user_item_matrix is not None else []
    all_books = books_df_from_pkl['judul'].tolist() if books_df_from_pkl is not None else []

    context = {
        'all_users': all_users,
        'all_books': all_books,
    }

    if request.method == 'POST':
        # Penanganan Tombol Collaborative
        if 'evaluate_collaborative' in request.POST:
            selected_user = request.POST.get('username')
            if selected_user:
                eval_data = evaluate_collaborative_detailed(selected_user)
                context.update({
                    'eval_type': 'collaborative',
                    'selected_user': selected_user,
                    'eval_data': eval_data
                })

        # Penanganan Tombol Content-Based
        elif 'evaluate_content' in request.POST:
            selected_book_title = request.POST.get('book_title')
            if selected_book_title:
                source_book_object = get_object_or_404(Book, title=selected_book_title)
                eval_data = evaluate_content_based_detailed(selected_book_title)
                context.update({
                    'eval_type': 'content_based',
                    'source_book': source_book_object,
                    'eval_data': eval_data
                })

        # --- BLOK BARU UNTUK HYBRID ---
        elif 'evaluate_hybrid' in request.POST:
            selected_user = request.POST.get('username_hybrid')  # Ambil dari form hybrid
            if selected_user:
                eval_data = evaluate_hybrid_detailed(selected_user)
                context.update({
                    'eval_type': 'hybrid',
                    'selected_user': selected_user,
                    'eval_data': eval_data
                })

    return render(request, 'sistem/evaluasi.html', context)
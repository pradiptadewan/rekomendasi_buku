from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import recommendation_service as rec
from .forms import LoginForm, RegisterForm
from .models import Book, Favorite

BOOKS_PER_PAGE = 12
SORT_OPTIONS = {
    'populer': ('Paling populer', ['-num_favorites', F('rating').desc(nulls_last=True), 'title']),
    'rating': ('Rating tertinggi', [F('rating').desc(nulls_last=True), 'title']),
    'judul': ('Judul (A–Z)', ['title']),
}


def _popular_books():
    return Book.objects.annotate(num_favorites=Count('favorites')).order_by(*SORT_OPTIONS['populer'][1])


def _redirect_back(request, fallback='sistem:dashboard'):
    """Kembali ke halaman asal (parameter `next`), hanya jika URL-nya aman."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(target, {request.get_host()}, request.is_secure()):
        return redirect(target)
    return redirect(fallback)


def _to_number(value, cast, minimum=None, maximum=None):
    """Ubah input form menjadi angka; kembalikan None jika kosong atau tidak valid."""
    try:
        number = cast(str(value).replace(',', '.'))
    except (TypeError, ValueError):
        return None
    if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
        return None
    return number


# ---------------------------------------------------------------------------
# Halaman umum
# ---------------------------------------------------------------------------

def home(request):
    return render(request, 'sistem/home.html', {
        'stats': rec.dataset_stats(),
        'popular_books': _popular_books()[:4],
    })


def dashboard(request):
    return render(request, 'sistem/dashboard.html', {
        'popular_books': _popular_books()[:8],
        'top_rated_books': Book.objects.order_by(*SORT_OPTIONS['rating'][1])[:8],
        'genres': rec.popular_genres(10),
    })


def book_list(request):
    query = request.GET.get('q', '').strip()
    genre = request.GET.get('genre', '').strip().lower()
    sort = request.GET.get('sort', 'populer')
    if sort not in SORT_OPTIONS:
        sort = 'populer'

    books = Book.objects.annotate(num_favorites=Count('favorites'))
    if query:
        books = books.filter(Q(title__icontains=query) | Q(author__icontains=query))
    if genre:
        # Cocokkan genre secara utuh di daftar "a, b, c".
        books = [b for b in books.filter(genre__icontains=genre).order_by(*SORT_OPTIONS[sort][1])
                 if genre in b.genre_list]
    else:
        books = books.order_by(*SORT_OPTIONS[sort][1])

    page_obj = Paginator(books, BOOKS_PER_PAGE).get_page(request.GET.get('page'))
    return render(request, 'sistem/book_list.html', {
        'page_obj': page_obj,
        'query': query,
        'genre': genre,
        'sort': sort,
        'sort_options': {key: label for key, (label, _) in SORT_OPTIONS.items()},
        'genres': rec.popular_genres(20),
    })


def book_detail(request, pk):
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'sistem/book_detail.html', {
        'book': book,
        'similar_items': rec.content_based(book.title, n=4),
    })


# ---------------------------------------------------------------------------
# Autentikasi
# ---------------------------------------------------------------------------

def login_view(request):
    if request.user.is_authenticated:
        return _redirect_back(request)
    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        if not form.cleaned_data.get('remember_me'):
            request.session.set_expiry(0)  # sesi berakhir saat browser ditutup
        messages.success(request, f'Selamat datang kembali, {form.get_user().username}!')
        return _redirect_back(request)
    return render(request, 'sistem/login.html', {'form': form, 'next': request.GET.get('next', '')})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('sistem:dashboard')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Akun {user.username} berhasil dibuat. Selamat datang!')
        return redirect('sistem:dashboard')
    return render(request, 'sistem/register.html', {'form': form})


@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, 'Anda telah keluar.')
    return redirect('sistem:home')


# ---------------------------------------------------------------------------
# Favorit
# ---------------------------------------------------------------------------

@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('book')
    return render(request, 'sistem/favorites.html', {'books': [f.book for f in favorites]})


@login_required
@require_POST
def favorite_add(request, pk):
    book = get_object_or_404(Book, pk=pk)
    _, created = Favorite.objects.get_or_create(user=request.user, book=book)
    if created:
        messages.success(request, f'"{book.title}" ditambahkan ke favorit.')
    else:
        messages.info(request, f'"{book.title}" sudah ada di favorit.')
    return _redirect_back(request, 'sistem:favorite_list')


@login_required
@require_POST
def favorite_remove(request, pk):
    book = get_object_or_404(Book, pk=pk)
    deleted, _ = Favorite.objects.filter(user=request.user, book=book).delete()
    if deleted:
        messages.success(request, f'"{book.title}" dihapus dari favorit.')
    return _redirect_back(request, 'sistem:favorite_list')


# ---------------------------------------------------------------------------
# Sistem rekomendasi
# ---------------------------------------------------------------------------

def recommend_hub(request):
    return render(request, 'sistem/recommend_hub.html')


def _selected_reader(request, param='user'):
    """Ambil nama pembaca dari query string; kembalikan (nama, pesan_error)."""
    username = request.GET.get(param, '').strip()
    if username and username not in rec.dataset_users():
        return username, f'Pembaca "{username}" tidak ada di dataset.'
    return username, None


def _selected_title(request, param='title'):
    title = request.GET.get(param, '').strip()
    if title and title not in rec.dataset_titles():
        return title, f'Buku "{title}" tidak ada di dataset. Pilih judul dari daftar saran.'
    return title, None


def collaborative_view(request):
    username, error = _selected_reader(request)
    context = {'all_users': rec.dataset_users(), 'selected_user': username, 'error': error}
    if username and not error:
        context['history'] = rec.user_history(username)
        context['items'] = rec.collaborative(username)
    return render(request, 'sistem/collaborative.html', context)


def content_based_view(request):
    mode = request.GET.get('mode')
    context = {
        'all_titles': rec.dataset_titles(),
        'available_genres': rec.popular_genres(16),
        'mode': mode,
    }

    if mode == 'title':
        title, error = _selected_title(request)
        context.update(searched_title=title, error=error)
        if title and not error:
            context['items'] = rec.content_based(title)
        elif not title:
            context['error'] = 'Masukkan judul buku terlebih dahulu.'

    elif mode == 'filter':
        genres = request.GET.getlist('genre')
        rating_min = _to_number(request.GET.get('rating'), float, 0, 5)
        max_pages = _to_number(request.GET.get('pages'), int, 1)
        context.update(selected_genres=genres, rating_min=rating_min, max_pages=max_pages)
        context['items'] = rec.filter_books(genres, rating_min, max_pages)

    return render(request, 'sistem/content_based.html', context)


def hybrid_view(request):
    username, error = _selected_reader(request)
    context = {'all_users': rec.dataset_users(), 'selected_user': username, 'error': error}
    if username and not error:
        context['items'] = rec.hybrid(username)
    return render(request, 'sistem/hybrid.html', context)


def evaluation_view(request):
    tab = request.GET.get('tab', 'collaborative')
    if tab not in ('collaborative', 'content', 'hybrid'):
        tab = 'collaborative'
    context = {'tab': tab, 'all_users': rec.dataset_users(), 'all_titles': rec.dataset_titles()}

    if tab == 'content':
        title, error = _selected_title(request)
        context.update(selected_title=title, error=error)
        if title and not error:
            context['source_book'] = Book.objects.filter(title=title).first()
            context['items'] = rec.content_based(title)
    else:
        username, error = _selected_reader(request)
        context.update(selected_user=username, error=error)
        if username and not error:
            if tab == 'collaborative':
                context['report'] = rec.evaluate_collaborative(username)
            else:
                context['report'] = rec.hybrid_report(username)

    return render(request, 'sistem/evaluation.html', context)

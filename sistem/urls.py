from django.urls import path
from . import views

# Disarankan untuk memberikan app_name untuk menghindari konflik nama URL dengan aplikasi lain
app_name = 'sistem'

urlpatterns = [
    # URL untuk Halaman Utama dan Rekomendasi

    path('', views.home, name='home'),
    path('input/', views.input_view, name='input'),  # Halaman untuk memasukkan username


    # URL untuk Autentikasi
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  # URL untuk logout ditambahkan
    # URL untuk Halaman Lain
    path('book/<int:book_id>/', views.book_detail_view, name='book_detail'),

    # URL untuk Dashboard
    path('dashboard-admin/', views.dashboard_admin, name='dashboard'),  # Tetap sebagai 'dashboard' untuk admin
    path('dashboard/', views.dashboard_user, name='dashboard_user'),
    # 'dashboard_user' menjadi halaman utama setelah login
    # URL untuk menampilkan halaman favorit
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorite/add/<int:book_id>/', views.add_to_favorite, name='add_to_favorite'),
    path('favorite/remove/<int:book_id>/', views.remove_from_favorite, name='remove_from_favorite'),
    path('books/popular/', views.all_popular_books_view, name='all_popular_books'),

    path('input/', views.input_view, name='input'),
    path('recommend/collaborative/', views.collaborative_view, name='collaborative'),
    path('recommend/content-based/', views.content_based_view, name='content_based'),
# Di urls.py, pastikan baris ini ada dan menunjuk ke view yang benar
    path('recommend/hybrid/', views.hybrid_view, name='hybrid'),
    path('recommend/evaluation/', views.evaluation_view, name='evaluation_view'),

]

from django.urls import path

from . import views

app_name = 'sistem'

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('books/', views.book_list, name='book_list'),
    path('books/<int:pk>/', views.book_detail, name='book_detail'),

    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    path('favorites/', views.favorite_list, name='favorite_list'),
    path('favorites/<int:pk>/add/', views.favorite_add, name='favorite_add'),
    path('favorites/<int:pk>/remove/', views.favorite_remove, name='favorite_remove'),

    path('recommend/', views.recommend_hub, name='recommend'),
    path('recommend/collaborative/', views.collaborative_view, name='collaborative'),
    path('recommend/content-based/', views.content_based_view, name='content_based'),
    path('recommend/hybrid/', views.hybrid_view, name='hybrid'),
    path('recommend/evaluation/', views.evaluation_view, name='evaluation'),
]

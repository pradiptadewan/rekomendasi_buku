from django.contrib import admin
from .models import Book, Favorite # Impor model Book dan Favorite

# Daftarkan model Anda di sini
admin.site.register(Book)
admin.site.register(Favorite)
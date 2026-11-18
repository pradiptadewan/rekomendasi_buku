from django.contrib import admin

from .models import Book, Favorite


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'genre', 'rating', 'page_count', 'has_cover')
    search_fields = ('title', 'author', 'genre')
    list_per_page = 50

    @admin.display(boolean=True, description='Sampul')
    def has_cover(self, obj):
        return bool(obj.image_url)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'created_at')
    list_filter = ('user',)
    search_fields = ('user__username', 'book__title')
    autocomplete_fields = ('book',)

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .genres import parse_genres


class Book(models.Model):
    title = models.CharField('judul', max_length=255, unique=True)
    author = models.CharField('penulis', max_length=255)
    image_url = models.URLField('URL sampul', max_length=500, null=True, blank=True)
    synopsis = models.TextField('sinopsis', null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    page_count = models.IntegerField('jumlah halaman', null=True, blank=True)
    genre = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'buku'
        verbose_name_plural = 'buku'

    def __str__(self):
        return self.title

    @property
    def genre_list(self):
        return parse_genres(self.genre)

    @property
    def cover_url(self):
        """URL sampul dengan HTTPS dan tanpa efek halaman terlipat (edge=curl) dari Google Books."""
        if not self.image_url:
            return ''
        return self.image_url.replace('http://', 'https://', 1).replace('&edge=curl', '')


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorites')
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='favorites')
    created_at = models.DateTimeField('ditambahkan', default=timezone.now, editable=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'favorit'
        verbose_name_plural = 'favorit'
        constraints = [
            models.UniqueConstraint(fields=['user', 'book'], name='unique_favorite_per_user'),
        ]

    def __str__(self):
        return f'{self.user.username} → {self.book.title}'

from django.db import models
from django.contrib.auth.models import User

# Model untuk menyimpan data setiap buku
class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    image_url = models.URLField(max_length=500, null=True, blank=True)
    synopsis = models.TextField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    genre = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.title

# Model untuk menandai buku mana yang menjadi favorit pengguna mana
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    class Meta:
        # Mencegah user mem-favoritkan buku yang sama lebih dari sekali
        unique_together = ('user', 'book')

    def __str__(self):
        return f"'{self.book.title}' is a favorite of {self.user.username}"
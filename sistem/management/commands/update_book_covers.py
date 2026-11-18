import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from sistem.models import Book

API_URL = 'https://www.googleapis.com/books/v1/volumes'


class Command(BaseCommand):
    help = 'Mengambil sampul buku dari Google Books API untuk buku yang belum punya sampul.'

    def add_arguments(self, parser):
        parser.add_argument('--delay', type=float, default=1.0, help='Jeda antar permintaan (detik).')

    def handle(self, *args, **options):
        books = Book.objects.filter(Q(image_url__isnull=True) | Q(image_url=''))
        total = books.count()
        if not total:
            self.stdout.write(self.style.SUCCESS('Semua buku sudah memiliki sampul.'))
            return

        self.stdout.write(f'Mencari sampul untuk {total} buku...')
        found = 0
        for book in books:
            params = {'q': f'intitle:{book.title} inauthor:{book.author}', 'maxResults': 1}
            if settings.GOOGLE_BOOKS_API_KEY:
                params['key'] = settings.GOOGLE_BOOKS_API_KEY
            try:
                response = requests.get(API_URL, params=params, timeout=10)
                response.raise_for_status()
                items = response.json().get('items') or []
                links = items[0].get('volumeInfo', {}).get('imageLinks', {}) if items else {}
                image_url = links.get('thumbnail') or links.get('smallThumbnail')
            except (requests.RequestException, ValueError) as exc:
                self.stdout.write(self.style.ERROR(f'Gagal memproses "{book.title}": {exc}'))
                image_url = None

            if image_url:
                book.image_url = image_url.replace('http://', 'https://', 1)
                book.save(update_fields=['image_url'])
                found += 1
                self.stdout.write(self.style.SUCCESS(f'Sampul ditemukan: "{book.title}"'))
            else:
                self.stdout.write(self.style.WARNING(f'Tidak ada sampul: "{book.title}"'))
            time.sleep(options['delay'])

        self.stdout.write(self.style.SUCCESS(f'Selesai: {found} dari {total} buku mendapat sampul.'))

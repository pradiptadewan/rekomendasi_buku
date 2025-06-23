import requests
import time
from django.core.management.base import BaseCommand
from django.conf import settings
from sistem.models import Book


class Command(BaseCommand):
    help = 'Mengambil URL gambar sampul dari Google Books API untuk buku yang belum memiliki gambar.'

    def handle(self, *args, **kwargs):
        # Ambil semua buku dari database yang kolom image_url-nya masih kosong
        books_to_update = Book.objects.filter(image_url__isnull=True)

        if not books_to_update.exists():
            self.stdout.write(self.style.SUCCESS('Semua buku sudah memiliki gambar sampul.'))
            return

        self.stdout.write(self.style.NOTICE(f'Menemukan {books_to_update.count()} buku untuk diperbarui...'))

        # Loop melalui setiap buku
        for book in books_to_update:
            try:
                # Membuat query pencarian berdasarkan judul dan penulis
                query = f"{book.title} {book.author}"
                api_key = settings.GOOGLE_BOOKS_API_KEY

                # Alamat API Google Books
                url = f"https://www.googleapis.com/books/v1/volumes?q={query}&key={api_key}"

                # Mengirim permintaan ke API
                response = requests.get(url)
                response.raise_for_status()  # Cek jika ada error HTTP

                data = response.json()

                # Mencari link gambar di dalam data JSON yang diterima
                if 'items' in data and len(data['items']) > 0:
                    volume_info = data['items'][0]['volumeInfo']
                    if 'imageLinks' in volume_info and 'thumbnail' in volume_info['imageLinks']:
                        image_url = volume_info['imageLinks']['thumbnail']

                        # Simpan URL gambar ke database
                        book.image_url = image_url
                        book.save()

                        self.stdout.write(self.style.SUCCESS(f'Berhasil menemukan sampul untuk: "{book.title}"'))
                    else:
                        self.stdout.write(self.style.WARNING(f'Tidak ada gambar untuk: "{book.title}"'))
                else:
                    self.stdout.write(self.style.WARNING(f'Tidak ada hasil untuk: "{book.title}"'))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error saat memproses "{book.title}": {e}'))

            # PENTING: Beri jeda 1 detik antar permintaan agar tidak dianggap spam oleh Google
            time.sleep(1)

        self.stdout.write(self.style.SUCCESS('Proses pembaruan gambar sampul selesai.'))
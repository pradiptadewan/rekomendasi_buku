import pandas as pd
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from sistem.models import Book

class Command(BaseCommand):
    help = 'Mengimpor atau memperbarui data buku dari file CSV ke dalam database'

    def handle(self, *args, **kwargs):
        csv_path = os.path.join(settings.BASE_DIR, 'sistem', 'static', 'data', 'gabungan_buku.csv')

        self.stdout.write(self.style.NOTICE(f"Membaca file dari: {csv_path}"))

        try:
            df = pd.read_csv(csv_path, encoding='latin-1', on_bad_lines='skip')

            # Membersihkan data terlebih dahulu
            df.dropna(subset=['judul', 'penulis'], inplace=True)
            df.drop_duplicates(subset=['judul'], inplace=True)

            # Loop melalui setiap baris di DataFrame
            for index, row in df.iterrows():
                # Gunakan update_or_create: jika judul sudah ada, perbarui datanya. Jika belum, buat baru.
                book, created = Book.objects.update_or_create(
                    title=row['judul'],  # Kunci untuk mencari buku
                    defaults={
                        'author': row['penulis'],
                        # Mengonversi ke tipe data yang benar dan menangani error
                        'rating': pd.to_numeric(row.get('rating'), errors='coerce'),
                        'page_count': pd.to_numeric(row.get('jml hlm'), errors='coerce'),
                        'genre': row.get('genre'),
                        'synopsis': row.get('sinopsis')
                    }
                )

                if created:
                    self.stdout.write(self.style.SUCCESS(f'Berhasil menambahkan: "{book.title}"'))
                else:
                    self.stdout.write(self.style.NOTICE(f'Berhasil memperbarui: "{book.title}"'))

            self.stdout.write(self.style.SUCCESS('Proses impor/update selesai.'))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR('Error: File CSV tidak ditemukan.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Terjadi error: {e}'))
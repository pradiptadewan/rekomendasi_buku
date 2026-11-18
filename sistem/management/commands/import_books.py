import pandas as pd
from django.core.management.base import BaseCommand, CommandError

from sistem.genres import parse_genres
from sistem.models import Book
from sistem.recommendation_service import CSV_PATH, load_dataset


def _clean(value, cast=None):
    if pd.isna(value):
        return None
    return cast(value) if cast else str(value).strip()


class Command(BaseCommand):
    help = 'Mengimpor atau memperbarui data buku dari sistem/data/gabungan_buku.csv ke database.'

    def handle(self, *args, **options):
        if not CSV_PATH.exists():
            raise CommandError(f'File CSV tidak ditemukan: {CSV_PATH}')

        books = load_dataset().drop_duplicates(subset=['judul'])
        created_count = updated_count = 0
        for row in books.to_dict('records'):
            _, created = Book.objects.update_or_create(
                title=row['judul'],
                defaults={
                    'author': _clean(row['penulis']),
                    'rating': _clean(row['rating'], float),
                    'page_count': _clean(row['jml hlm'], int),
                    'genre': ', '.join(parse_genres(row['genre'])) or None,
                    'synopsis': _clean(row['sinopsis']),
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Selesai: {created_count} buku baru, {updated_count} buku diperbarui.'
        ))

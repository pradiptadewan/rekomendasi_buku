import re

from django.db import migrations

MOJIBAKE_MARKERS = ('Ã', 'Â', 'â€')
MISSING_SEPARATOR = re.compile(r'(?<=[a-z])young-adult\s*')


def fix_mojibake(text):
    """Perbaiki teks UTF-8 yang dulu terbaca sebagai latin-1 (contoh: "PappÃ©" -> "Pappé")."""
    if not text or not any(marker in text for marker in MOJIBAKE_MARKERS):
        return text
    try:
        return text.encode('latin-1').decode('utf-8')
    except UnicodeError:
        return text


def normalize_genre(text):
    if not text:
        return text
    text = MISSING_SEPARATOR.sub(', young-adult, ', text.lower())
    genres = []
    for part in text.split(','):
        genre = 'young-adult' if part.strip() == 'ya' else part.strip()
        if genre and genre not in genres:
            genres.append(genre)
    return ', '.join(genres)


def clean_books(apps, schema_editor):
    Book = apps.get_model('sistem', 'Book')
    for book in Book.objects.all():
        changed = {
            'synopsis': fix_mojibake(book.synopsis),
            'genre': normalize_genre(book.genre),
            'image_url': book.image_url.replace('http://', 'https://', 1) if book.image_url else book.image_url,
        }
        changed = {field: value for field, value in changed.items() if value != getattr(book, field)}
        if changed:
            Book.objects.filter(pk=book.pk).update(**changed)


class Migration(migrations.Migration):

    dependencies = [
        ('sistem', '0004_book_unique_title_favorite_created_at'),
    ]

    operations = [
        migrations.RunPython(clean_books, migrations.RunPython.noop),
    ]

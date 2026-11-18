import re

# Di dataset ada genre yang komanya hilang, misalnya "romansayoung-adult misteri".
_MISSING_SEPARATOR = re.compile(r'(?<=[a-z])young-adult\s*')
_ALIASES = {'ya': 'young-adult'}


def parse_genres(text):
    """Ubah teks genre ("fiksi, misteri") menjadi list genre huruf kecil yang unik, urutan tetap."""
    if not isinstance(text, str):
        return []
    text = _MISSING_SEPARATOR.sub(', young-adult, ', text.lower())
    genres = []
    for part in text.split(','):
        genre = _ALIASES.get(part.strip(), part.strip())
        if genre and genre not in genres:
            genres.append(genre)
    return genres

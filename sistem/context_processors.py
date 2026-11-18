def favorites(request):
    """Sediakan ID buku favorit user di semua template, untuk menandai tombol favorit."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {'favorite_ids': set()}
    return {'favorite_ids': set(user.favorites.values_list('book_id', flat=True))}

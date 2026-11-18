from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from . import recommendation_service as rec
from .genres import parse_genres
from .models import Book, Favorite


class GenreParsingTests(TestCase):
    def test_splits_and_normalizes(self):
        self.assertEqual(parse_genres('Fiksi, Misteri ,fiksi'), ['fiksi', 'misteri'])

    def test_fixes_missing_separator(self):
        self.assertEqual(parse_genres('romansayoung-adult misteri'), ['romansa', 'young-adult', 'misteri'])

    def test_empty_values(self):
        self.assertEqual(parse_genres(None), [])
        self.assertEqual(parse_genres(''), [])


class RecommendationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_books', stdout=StringIO())

    def test_data_loaded(self):
        stats = rec.dataset_stats()
        self.assertEqual(stats['books'], Book.objects.count())

    def test_content_based_works_for_every_book(self):
        # Dulu index .pkl dipakai sebagai nomor baris, sehingga sebagian besar buku tidak mendapat hasil.
        for title in rec.dataset_titles():
            items = rec.content_based(title)
            self.assertEqual(len(items), 5, title)
            self.assertNotIn(title, [i['book'].title for i in items])

    def test_content_based_scores_sorted(self):
        scores = [i['score'] for i in rec.content_based('86')]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_filter_matches_whole_genre(self):
        items = rec.filter_books(['fiksi'], n=400)
        self.assertTrue(items)
        for item in items:
            self.assertIn('fiksi', item['book'].genre_list)

    def test_filter_respects_rating_and_pages(self):
        for item in rec.filter_books([], rating_min=4.2, max_pages=250, n=400):
            self.assertGreaterEqual(item['book'].rating, 4.2)
            self.assertLessEqual(item['book'].page_count, 250)

    def test_collaborative_excludes_history(self):
        for username in rec.dataset_users()[:40]:
            history = {h['title'] for h in rec.user_history(username)}
            for item in rec.collaborative(username):
                self.assertNotIn(item['book'].title, history)

    def test_hybrid_page_matches_evaluation(self):
        for username in rec.dataset_users()[:20]:
            report = rec.hybrid_report(username)
            ranked = [r['title'] for r in report['ranked']]
            self.assertEqual(len(ranked), len(set(ranked)), 'tidak boleh ada judul ganda')
            self.assertEqual([r['title'] for r in report['recommendations']], ranked[:5])
            self.assertEqual([r['title'] for r in rec.hybrid(username)], ranked[:5])

    def test_unknown_inputs_return_empty(self):
        self.assertEqual(rec.content_based('Judul yang tidak ada'), [])
        self.assertEqual(rec.collaborative('@tidak_ada'), [])
        self.assertIsNone(rec.hybrid_report('@tidak_ada'))


class PageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('import_books', stdout=StringIO())
        cls.user = User.objects.create_user('pembaca', 'p@example.com', 'rahasia-123')
        cls.book = Book.objects.get(title='86')
        cls.reader = rec.dataset_users()[0]

    def test_public_pages(self):
        urls = [
            reverse('sistem:home'),
            reverse('sistem:dashboard'),
            reverse('sistem:book_list'),
            reverse('sistem:book_list') + '?q=okky&genre=fiksi&sort=rating&page=1',
            reverse('sistem:book_detail', args=[self.book.pk]),
            reverse('sistem:login'),
            reverse('sistem:register'),
            reverse('sistem:recommend'),
            reverse('sistem:collaborative') + f'?user={self.reader}',
            reverse('sistem:content_based') + '?mode=title&title=86',
            reverse('sistem:content_based') + '?mode=filter&genre=fiksi&rating=4&pages=300',
            reverse('sistem:content_based') + '?mode=filter&rating=abc',
            reverse('sistem:hybrid') + f'?user={self.reader}',
            reverse('sistem:evaluation') + f'?tab=collaborative&user={self.reader}',
            reverse('sistem:evaluation') + '?tab=content&title=86',
            reverse('sistem:evaluation') + f'?tab=hybrid&user={self.reader}',
            reverse('sistem:collaborative') + '?user=@tidak_ada',
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_favorites_require_login(self):
        response = self.client.get(reverse('sistem:favorite_list'))
        self.assertRedirects(response, reverse('sistem:login') + '?next=' + reverse('sistem:favorite_list'))

    def test_login_redirects_to_next(self):
        target = reverse('sistem:book_detail', args=[self.book.pk])
        response = self.client.post(reverse('sistem:login') + f'?next={target}', {
            'username': 'pembaca', 'password': 'rahasia-123', 'next': target,
        })
        self.assertRedirects(response, target)

    def test_login_ignores_external_next(self):
        response = self.client.post(reverse('sistem:login'), {
            'username': 'pembaca', 'password': 'rahasia-123', 'next': 'https://contoh-jahat.com/',
        })
        self.assertRedirects(response, reverse('sistem:dashboard'))

    def test_add_and_remove_favorite(self):
        self.client.force_login(self.user)
        back = reverse('sistem:book_list')
        add_url = reverse('sistem:favorite_add', args=[self.book.pk])

        self.assertEqual(self.client.get(add_url).status_code, 405)  # harus POST
        self.assertRedirects(self.client.post(add_url, {'next': back}), back)
        self.assertTrue(Favorite.objects.filter(user=self.user, book=self.book).exists())

        self.client.post(reverse('sistem:favorite_remove', args=[self.book.pk]), {'next': back})
        self.assertFalse(Favorite.objects.filter(user=self.user, book=self.book).exists())

    def test_logout_requires_post(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('sistem:logout')).status_code, 405)
        self.client.post(reverse('sistem:logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_register_logs_in(self):
        response = self.client.post(reverse('sistem:register'), {
            'username': 'baru', 'email': 'baru@example.com',
            'password1': 'Kata-Sandi-Kuat-99', 'password2': 'Kata-Sandi-Kuat-99',
        })
        self.assertRedirects(response, reverse('sistem:dashboard'))
        self.assertEqual(int(self.client.session['_auth_user_id']), User.objects.get(username='baru').pk)

    def test_register_rejects_duplicate_email(self):
        response = self.client.post(reverse('sistem:register'), {
            'username': 'lain', 'email': 'P@example.com',
            'password1': 'Kata-Sandi-Kuat-99', 'password2': 'Kata-Sandi-Kuat-99',
        })
        self.assertContains(response, 'Email ini sudah terdaftar.')

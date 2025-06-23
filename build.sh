#!/usr/bin/env bash
# exit on error
set -o errexit

# Perintah untuk menginstall semua perkakas dari daftar belanja
pip install -r requirements.txt

# Perintah untuk mengumpulkan semua file statis (CSS, JS, gambar) ke satu tempat
python manage.py collectstatic --no-input

# Perintah untuk menjalankan migrasi database
python manage.py migrate

# Perintah untuk mengisi database buku dari CSV (jika perlu dijalankan saat deploy)
# python manage.py import_books
#!/usr/bin/env bash
# exit on error
set -o errexit

# Vercel akan otomatis menjalankan 'pip install' sebelum script ini.
# Jadi kita hanya perlu menjalankan perintah spesifik Django.

python manage.py collectstatic --no-input
python manage.py migrate
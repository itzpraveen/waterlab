#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r requirements.txt

# Run tests
python manage.py test

# Collect static files
python manage.py collectstatic --noinput

# Run database migrations
python manage.py migrate

# Fix admin role case sensitivity issue
python manage.py fix_admin_role

# Create admin user automatically (if not exists)
python manage.py create_admin

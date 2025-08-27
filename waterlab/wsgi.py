"""
WSGI config for waterlab project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

# Prefer Render-specific settings when running on Render.
# Falls back to default development settings otherwise.
if os.environ.get('DJANGO_SETTINGS_MODULE'):
    # Respect an explicitly provided module
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', os.environ['DJANGO_SETTINGS_MODULE'])
elif os.environ.get('RENDER') or os.environ.get('RENDER_EXTERNAL_HOSTNAME') or os.environ.get('PORT'):
    # Heuristics that indicate Render environment
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waterlab.settings_render')
else:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'waterlab.settings')

application = get_wsgi_application()

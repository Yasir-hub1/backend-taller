"""
ASGI config for emergency vehicle platform.

Configurado para soportar Server-Sent Events (SSE) con django-eventstream.
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core.asgi import get_asgi_application
import django_eventstream

# Aplicación HTTP estándar de Django
django_asgi_app = get_asgi_application()

# Aplicación ASGI completa con soporte para SSE
application = django_asgi_app

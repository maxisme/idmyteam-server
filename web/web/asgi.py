"""
ASGI config for web project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from opentelemetry.ext.asgi import OpenTelemetryMiddleware

from web.trace import set_tracing_exporter, get_default_span_name

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
set_tracing_exporter()
application = get_asgi_application()
application = OpenTelemetryMiddleware(application, get_default_span_name)

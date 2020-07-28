"""
WSGI config for web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from opentelemetry import trace
from opentelemetry.ext import jaeger
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleExportSpanProcessor, BatchExportSpanProcessor

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
os.environ.setdefault("OPENTELEMETRY_PYTHON_DJANGO_INSTRUMENT", "True")

jaeger_collector_host_name = os.environ.get("JAEGER_COLLECTOR_HOST_NAME", False)
trace.set_tracer_provider(TracerProvider())

if not jaeger_collector_host_name:
    # print tracer
    trace.get_tracer_provider().add_span_processor(
        SimpleExportSpanProcessor(ConsoleSpanExporter())
    )
else:
    # jaeger tracer
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name="traefik",
        collector_host_name=jaeger_collector_host_name,
        collector_port=14268,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(jaeger_exporter)
    )

application = get_wsgi_application()
application = OpenTelemetryMiddleware(application)

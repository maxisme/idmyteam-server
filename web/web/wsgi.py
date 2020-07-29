"""
WSGI config for web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""
import logging
import os
import socket

from django.core.wsgi import get_wsgi_application
from opentelemetry import trace, propagators
from opentelemetry.ext import jaeger
from opentelemetry.ext.wsgi import OpenTelemetryMiddleware
from opentelemetry.sdk.trace import (
    TracerProvider,
    Resource,
)
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
    BatchExportSpanProcessor,
)
from opentelemetry.sdk.trace.propagation.b3_format import B3Format

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
os.environ.setdefault("OPENTELEMETRY_PYTHON_DJANGO_INSTRUMENT", "True")

trace.set_tracer_provider(
    TracerProvider(resource=Resource({"hostname": socket.gethostname()}))
)
propagators.set_global_httptextformat(B3Format())

# jaeger tracer
jaeger_exporter = jaeger.JaegerSpanExporter(
    service_name="traefik",
    collector_host_name=jaeger_collector_host_name,
    collector_port=14268,
)
trace.get_tracer_provider().add_span_processor(
    BatchExportSpanProcessor(jaeger_exporter)
)


def get_default_span_name(environ):
    logging.error(environ)
    return "{} Request".format(environ.get("REQUEST_METHOD", "")).strip()


application = get_wsgi_application()
application = OpenTelemetryMiddleware(application, get_default_span_name)

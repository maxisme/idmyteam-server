"""
WSGI config for web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""
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
    BatchExportSpanProcessor,
)
from opentelemetry.sdk.trace.propagation.b3_format import B3Format

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
os.environ.setdefault("OPENTELEMETRY_PYTHON_DJANGO_INSTRUMENT", "True")
jaeger_collector_host_name = os.environ.get("JAEGER_COLLECTOR_HOST_NAME", False)

if jaeger_collector_host_name:
    hostname = socket.gethostname()
    _, _, ips = socket.gethostbyaddr(hostname)
    trace.set_tracer_provider(
        TracerProvider(resource=Resource({"hostname": hostname, "hostname_ip": str(ips)}))
    )
    propagators.set_global_httptextformat(B3Format())

    # jaeger tracer
    jaeger_exporter = jaeger.JaegerSpanExporter(
        service_name="ID My Team",
        collector_host_name=jaeger_collector_host_name,
        collector_port=14268,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(jaeger_exporter)
    )


def get_default_span_name(environ):
    return "{} {}".format(environ.get("REQUEST_METHOD", ""), environ.get("PATH_INFO", "")).strip()


application = get_wsgi_application()
application = OpenTelemetryMiddleware(application, get_default_span_name)

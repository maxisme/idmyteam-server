"""
WSGI config for web project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/howto/deployment/wsgi/
"""
import os
import socket

from opentelemetry import trace, propagators
from opentelemetry.ext import jaeger
from opentelemetry.ext.psycopg2 import Psycopg2Instrumentor
from opentelemetry.sdk.trace import (
    TracerProvider,
    Resource,
)
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
)
from opentelemetry.sdk.trace.propagation.b3_format import B3Format


def set_tracing_exporter():
    DOCKER_NETWORK_TRAEFIK_SUBNET = "10.0.1."

    os.environ.setdefault("OPENTELEMETRY_PYTHON_DJANGO_INSTRUMENT", "True")
    jaeger_collector_host_name = os.environ.get("JAEGER_COLLECTOR_HOST_NAME", False)

    if jaeger_collector_host_name:
        hostname = socket.gethostname()
        _, _, ips = socket.gethostbyname_ex(hostname)

        labels = {"hostname": hostname}
        for i, ip in enumerate(ips):
            labels[f"hostname-ip-{i + 1}"] = ip
            if DOCKER_NETWORK_TRAEFIK_SUBNET in ip:
                labels["traefik-server-ip"] = ip
        labels["commit-hash"] = os.getenv("COMMIT_HASH")

        trace.set_tracer_provider(TracerProvider(resource=Resource(labels)))
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

        # postgres tracing
        Psycopg2Instrumentor().instrument()


def get_default_span_name(environ):
    return "{} {}".format(
        environ.get("REQUEST_METHOD", ""), environ.get("PATH_INFO", "")
    ).strip()

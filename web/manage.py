#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

from opentelemetry import trace
from opentelemetry.ext import jaeger
from opentelemetry.ext.django import DjangoInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchExportSpanProcessor,
    SimpleExportSpanProcessor,
    ConsoleSpanExporter,
)


def main():
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

    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("started ID My Team"):
        pass

    DjangoInstrumentor().instrument()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

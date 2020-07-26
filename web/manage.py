#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from opentelemetry.ext.django import DjangoInstrumentor
from opentelemetry.ext import jaeger
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchExportSpanProcessor, SimpleExportSpanProcessor, ConsoleSpanExporter)
from web.settings import DEBUG

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
    os.environ.setdefault("OPENTELEMETRY_PYTHON_DJANGO_INSTRUMENT", "True")

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    if DEBUG:
        # print tracer
        trace.get_tracer_provider().add_span_processor(
            SimpleExportSpanProcessor(ConsoleSpanExporter())
        )
    else:
        # jaeger tracer
        jaeger_exporter = jaeger.JaegerSpanExporter(
            service_name='ID My Team',
            collector_host_name='jaeger-collector',
            collector_port=14268
        )
        trace.get_tracer_provider().add_span_processor(BatchExportSpanProcessor(jaeger_exporter))

    with tracer.start_as_current_span('started ID My Team'):
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

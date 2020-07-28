import os

from django.http import HttpResponse
from django.shortcuts import render  # just for pycharm to create links to templates
from opentelemetry import trace
from opentelemetry.ext import jaeger
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchExportSpanProcessor
from opentelemetry.sdk.trace.export import (
    ConsoleSpanExporter,
    SimpleExportSpanProcessor,
)

from idmyteamserver.helpers import render

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
        service_name="ID My Team",
        collector_host_name=jaeger_collector_host_name,
        collector_port=14268,
    )
    trace.get_tracer_provider().add_span_processor(
        BatchExportSpanProcessor(jaeger_exporter)
    )


def welcome_handler(request):
    return render(request, "welcome.html")


def about_handler(request):
    return render(request, "about.html", {"title": "About"})


def contact_handler(request):
    return render(request, "contact.html", {"title": "Contact"})


def terms_handler(request):
    return render(request, "terms.html", {"title": "Terms"})


def storage_handler(request):
    return render(request, "storage.html", {"title": "Image Storage"})


def tutorials_handler(request):
    return render(request, "tutorials/list.html", {"title": "Tutorials"})


def trace_hander(request):
    tracer = trace.get_tracer(__name__)

    with tracer.start_as_current_span("hey ho hit the trace"):
        pass

    return HttpResponse(
        str(request.headers.items())
    )


def tutorial_hander(request, slug):
    title = slug.replace("-", " ").title()
    path = "tutorials/" + slug + ".html"
    return render(request, path, {"title": title})

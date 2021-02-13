import os

from django.http import HttpResponse
from django.shortcuts import render  # just for pycharm to create links to templates
from opentelemetry import trace

from idmyteam.idmyteam.helpers import render


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


def trace_handler(request):  # pragma: no cover
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("here is a trace"):
        return HttpResponse(str(request.headers.items()))


def health_handler(request):  # pragma: no cover
    return HttpResponse()


def commit_hash_handler(request):  # pragma: no cover
    return HttpResponse(os.getenv("COMMIT_HASH"))


def tutorial_handler(request, slug):
    title = slug.replace("-", " ").title()
    path = "tutorials/" + slug + ".html"
    return render(request, path, {"title": title})

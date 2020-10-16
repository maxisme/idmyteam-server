import os

import redis
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.http import HttpResponse
from django.shortcuts import render  # just for pycharm to create links to templates
from opentelemetry import trace
from django.db import connection

from idmyteamserver.helpers import render
from idmyteamserver.models import Team
from idmyteamserver.structs import WSStruct
from web.settings import REDIS_CONN


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

    with tracer.start_as_current_span("here is a trace"):
        pass

    return HttpResponse(str(request.headers.items()))


def health_handler(request):
    # check db
    connection.connect()
    if not connection.is_usable():
        return HttpResponse(content=b'db down', status=500)

    # check redis
    try:
        REDIS_CONN.client_list()
    except redis.ConnectionError:
        return HttpResponse(content=b'redis down', status=500)

    return HttpResponse(status=200)


def commit_hash_handler(request):
    return HttpResponse(os.getenv("COMMIT_HASH"))


def tutorial_hander(request, slug):
    title = slug.replace("-", " ").title()
    path = "tutorials/" + slug + ".html"
    return render(request, path, {"title": title})

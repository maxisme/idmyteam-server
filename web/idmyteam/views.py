from django.http import HttpResponse
from django.template import loader
from jinja2 import Environment
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static_url': staticfiles_storage.url,
        'url': reverse,
    })
    return env

import os
from os.path import dirname, abspath

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def define(val=None):
    return val


@register.simple_tag
def include_file(file_name):
    file = open(file_name).read()
    return mark_safe(file)


@register.simple_tag
def get_logo():
    parent_dir = dirname(dirname(abspath(__file__)))
    svg_logo_path = os.path.join(parent_dir, "static/images/icon.svg")
    file = open(svg_logo_path).read()
    return mark_safe(file)

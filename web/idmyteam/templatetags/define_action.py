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

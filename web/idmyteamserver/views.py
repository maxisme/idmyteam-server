from django.http import HttpResponse
from django.shortcuts import render  # just for pycharm to create links to templates
from django.template import loader

z
def render(request, template_name, context={}, content_type=None, status=None, using=None):
    """
    Return a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """

    # add global context
    c = {
        "title": "",
        "meta": {
            "description": "A recognition system for your team.",
            "keywords": "detect, recognise, facial, detection, team, id, recogniser, id my team, idmy.team",
        },
        "username": request.COOKIES.get("username"),
        "error_message": request.COOKIES.get("error_message"),
        "success_message": request.COOKIES.get("success_message"),
    }

    if context.get("username", False):
        context["username"] = context["username"].decode("utf-8")

    content = loader.render_to_string(template_name, {**c, **context}, request, using=using)
    resp = HttpResponse(content, content_type, status)

    # remove flash messages
    resp.set_cookie("error_message")
    resp.set_cookie("success_message")

    return resp


def welcome_handler(request):
    return render(request, 'welcome.html')


def about_handler(request):
    return render(request, 'about.html', {'title': 'About'})


def contact_handler(request):
    return render(request, 'contact.html', {'title': 'Contact'})


def terms_handler(request):
    return render(request, 'terms.html', {'title': 'Terms'})


def storage_handler(request):
    return render(request, 'storage.html', {'title': 'Image Storage'})


def tutorials_handler(request):
    return render(request, 'tutorials/list.html', {'title': 'Tutorials'})


def tutorial_hander(request, slug):
    title = slug.replace("-", " ").title()
    path = "tutorials/" + slug + ".html"
    return render(request, path, {'title': title})

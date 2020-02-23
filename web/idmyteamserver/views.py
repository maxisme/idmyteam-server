from django.shortcuts import render  # just for pycharm to create links to templates
from idmyteamserver.helpers import render


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

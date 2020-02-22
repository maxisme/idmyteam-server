"""web URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from idmyteamserver import views

urlpatterns = [
    path('', views.welcome_handler),
    path('about', views.about_handler),
    path('contact', views.contact_handler),
    path('terms', views.terms_handler),
    path('storage', views.storage_handler),
    path('tutorials', views.tutorials_handler),
    path("tutorials/<slug:slug>", views.tutorial_hander)
]

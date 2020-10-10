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

from idmyteamserver import views, auth, api

# REMEMBER: update sitemap.py
urlpatterns = [
    path("", views.welcome_handler, name='main'),
    path("about", views.about_handler, name='about'),
    path("contact", views.contact_handler, name='contact'),
    path("terms", views.terms_handler, name='terms'),
    path("storage", views.storage_handler, name='storage_terms'),
    path("tutorials", views.tutorials_handler, name='tutorials'),
    path("tutorials/<slug:slug>", views.tutorial_hander),
    path("signup", auth.signup_handler, name='signup'),
    path("login", auth.login_handler, name='login'),
    path("profile", auth.profile_handler, name='profile'),
    path("logout", auth.logout_handler),
    path("forgot", auth.forgot_handler),
    path("reset", auth.reset_handler),
    path("confirm/<key>", auth.confirm_handler),
    path("reset-credentials", api.reset_credentials_handler),
    path("toggle-storage", api.toggle_storage_handler),
    path("trace", views.trace_hander),
    path("health", views.health_handler),
    path("commit-hash", views.commit_hash_handler),
]

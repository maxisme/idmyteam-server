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

urlpatterns = [
    path("", views.welcome_handler),
    path("about", views.about_handler),
    path("contact", views.contact_handler),
    path("terms", views.terms_handler),
    path("storage", views.storage_handler),
    path("tutorials", views.tutorials_handler),
    path("tutorials/<slug:slug>", views.tutorial_hander),
    path("signup", auth.signup_handler),
    path("login", auth.login_handler),
    path("logout", auth.logout_handler),
    path("forgot", auth.forgot_handler),
    path("reset", auth.reset_handler),
    path("confirm/<key>", auth.confirm_handler),
    path("profile", auth.profile_handler),
    path("reset-credentials", api.reset_credentials_handler),
    path("toggle-storage", api.toggle_storage_handler),
    path("trace", views.trace_hander),
    path("health", views.health_handler),
]

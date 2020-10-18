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

PUBLIC_URL_NAMES = [
    "main",
    "about",
    "contact",
    "terms",
    "storage_terms",
    "tutorials",
    "signup",
    "login",
    "forgot-password",
]

AUTH_URL_NAMES = ["profile"]

# REMEMBER: update sitemap.py
urlpatterns = [
    path("", views.welcome_handler, name="main"),
    path("about", views.about_handler, name="about"),
    path("contact", views.contact_handler, name="contact"),
    path("terms", views.terms_handler, name="terms"),
    path("storage", views.storage_handler, name="storage_terms"),
    path("tutorials", views.tutorials_handler, name="tutorials"),
    path("tutorials/<slug:slug>", views.tutorial_hander),
    path("signup", auth.signup_handler, name="signup"),
    path("login", auth.login_handler, name="login"),
    path("profile", auth.profile_handler, name="profile"),
    path("logout", auth.logout_handler, name="logout"),
    path("forgot", auth.forgot_handler, name="forgot-password"),
    path("reset", auth.reset_handler, name="reset-password"),
    path("confirm/<key>", auth.confirm_handler, name="confirm-email"),
    path("reset-credentials", api.reset_credentials_handler, name="reset-credentials"),
    path(
        "toggle-storage", api.toggle_image_storage_handler, name="toggle-image-storage"
    ),
    path("trace", views.trace_hander),
    path("health", views.health_handler),
    path("commit-hash", views.commit_hash_handler),
]

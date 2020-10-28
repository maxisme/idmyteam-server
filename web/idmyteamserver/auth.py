import logging

from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponseNotFound

from idmyteamserver import forms
from idmyteamserver import email
from idmyteamserver.helpers import (
    SUCCESS_COOKIE_KEY,
    is_valid_email,
    redirect,
    ERROR_COOKIE_KEY,
    random_str,
)
from idmyteamserver.models import Team
from idmyteamserver.views import render
from web.settings import PASS_RESET_TOKEN_LEN
from django.forms.models import model_to_dict

clients = {}


@login_required(login_url="/login")
def profile_handler(request):
    team: Team = request.user
    context = model_to_dict(team)
    context["root_password"] = random_str(30)
    return render(
        request, "profile.html", context=context
    )  # TODO maybe just pass whole user


INVALID_LOGIN_MESSAGE = "Invalid credentials! Please try again."
INVALID_SIGNUP_MESSAGE = (
    "Error with user information! Please try a different username or email"
)


def login_handler(request):
    error_message = ""
    if request.method == "POST":
        form = forms.LoginForm(request.POST)
        if form.is_valid():
            team: Team = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if team:
                if team.is_confirmed:
                    login(request, team)
                    return HttpResponseRedirect("/profile")
                else:
                    logout(request)
                    error_message = f"""
                    You have not confirmed your email! <a href='/resend?email={team.email}'>Resend confirmation?</a>
                    """
            else:
                error_message = INVALID_LOGIN_MESSAGE
    else:
        form = forms.LoginForm()

    return render(
        request,
        "forms/login.html",
        {"title": "Login", "form": form},
        error_message=error_message,
    )


SUCCESS_SIGNUP_MSG = "Welcome! Please confirm your email to complete signup!"
IGNORED_INPUTS = ("confirm", "terms", "captcha")


def signup_handler(request):
    if request.method == "POST":
        form = forms.SignUpForm(request.POST)
        if form.is_valid():
            post_data = form.cleaned_data
            for key in IGNORED_INPUTS:
                del post_data[key]

            team = Team.objects.create_user(**post_data)
            if team:
                # send confirmation email
                email.send_confirm(
                    request,
                    to=form.cleaned_data.get("email"),
                    key=team.confirmation_key,
                )

                return redirect(
                    "/",
                    cookies={SUCCESS_COOKIE_KEY: SUCCESS_SIGNUP_MSG},
                )
    else:
        form = forms.SignUpForm()

    return render(request, "forms/signup.html", {"title": "Sign Up", "form": form})


def confirm_handler(request, key):
    team_email = request.GET.get("email", None)
    if is_valid_email(team_email):
        team = Team.objects.get(email=team_email)
        if team:
            email = None
            try:
                email = team.confirm_email(key)
            except Exception as e:
                logging.error(e)

            if email:
                return redirect(
                    "/",
                    cookies={
                        SUCCESS_COOKIE_KEY: f"Confirmed! Welcome to the Team {team}!"
                    },
                )
    return redirect(
        "/",
        cookies={
            ERROR_COOKIE_KEY: "Problem confirming your team account! Please try again."
        },
    )


def forgot_handler(request):
    if request.method == "POST":
        form = forms.ForgotForm(request.POST)
        if form.is_valid():
            username_email = form.cleaned_data.get("username_email")
            if is_valid_email(
                username_email
            ):  # TODO prevent username being a valid email
                team = Team.objects.get(email=username_email)
            else:
                team = Team.objects.get(username=username_email)

            if team:
                # store reset key
                team.password_reset_token = random_str(PASS_RESET_TOKEN_LEN)
                team.save()

                # send reset key
                email.send_reset(request, to=team.email, key=team.password_reset_token)

        return redirect(
            "/",
            cookies={
                SUCCESS_COOKIE_KEY: "If the username or email exists you will receive a password reset to your email!"
            },
        )
    else:
        form = forms.ForgotForm()

    return render(
        request, "forms/forgot.html", {"title": "Forgot Password", "form": form}
    )


def reset_handler(request):
    if request.method == "GET":
        key = request.GET.get("key", "")
        if len(key) == PASS_RESET_TOKEN_LEN:
            form = forms.ResetForm(initial={"reset_key": key})
        else:
            return HttpResponseNotFound()
    else:
        form = forms.ResetForm(request.POST)
        if form.is_valid():
            team = Team.objects.get(
                password_reset_token=form.cleaned_data.get("reset_key")
            )
            if team:
                team.password_reset_token = ""
                team.set_password(form.cleaned_data.get("password"))
                team.save()

                return redirect(
                    "/", cookies={SUCCESS_COOKIE_KEY: "Successfully reset password!"}
                )

    return render(
        request, "forms/reset.html", {"title": "Reset Password", "form": form}
    )


def logout_handler(request):
    logout(request)
    return redirect("/")

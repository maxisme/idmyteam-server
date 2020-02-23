from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

ERROR_COOKIE_KEY = "error_message"
SUCCESS_COOKIE_KEY = "success_message"


def render(request, template_name, context={}, cookies={}, redirect="", content_type=None, status=None, using=None):
    """
    Return a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    if redirect:
        resp = HttpResponseRedirect(redirect)
    else:
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
        resp.set_cookie(ERROR_COOKIE_KEY)
        resp.set_cookie(SUCCESS_COOKIE_KEY)

    # add cookies
    for key, val in cookies:
        resp.set_cookie(key, val)

    return resp

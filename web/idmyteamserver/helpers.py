from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

SUCCESS_COOKIE_KEY = "success_message"

def render(
    request,
    redirect=None,
    template_name=None,
    context={},
    cookies={},
    content_type=None,
    status=None,
    using=None,
    **kwargs
):
    """
    Return a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    if redirect:
        resp = HttpResponseRedirect(redirect)
    else:
        # set global context values
        c = {
            "title": "",
            "meta": {
                "description": "A recognition system for your team.",
                "keywords": "detect, recognise, facial, recognition, facial recognition, detection, team, id, recogniser, ID My Team, idmy.team",
            },
            "username": request.COOKIES.get("username"),
            **kwargs
        }

        if context.get("username", False):
            context["username"] = context["username"].decode("utf-8")

        content = loader.render_to_string(
            template_name, {**c, **context}, request, using=using
        )
        resp = HttpResponse(content, content_type, status)

        # remove flash success cookie
        resp.set_cookie(SUCCESS_COOKIE_KEY)

    # add cookies
    for key in cookies:
        resp.set_cookie(key, cookies[key])

    return resp

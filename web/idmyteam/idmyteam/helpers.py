import random
import re
import string
from functools import lru_cache

from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader

# from worker.queue import enqueue
from web.settings import CREDENTIAL_LEN

SUCCESS_COOKIE_KEY = "success_message"
ERROR_COOKIE_KEY = "error_message"


def redirect(path, cookies={}):
    resp = HttpResponseRedirect(path)

    # add cookies
    for key in cookies:
        resp.set_cookie(key, cookies[key])

    return resp


def render(
    request,
    template_name=None,
    context={},
    content_type=None,
    status=None,
    using=None,
    **kwargs,
):
    """
    Return a HttpResponse whose content is filled with the result of calling
    django.template.loader.render_to_string() with the passed arguments.
    """
    # set global context values
    c = {
        "title": "",
        "meta": {
            "description": "A recognition system for your team.",
            "keywords": "detect, recognise, facial, worker, facial worker, detection, team, id, recogniser, ID My Team, idmy.team",
        },
        "logged_in": request.user.is_authenticated,
        **request.COOKIES,
        **kwargs,
    }

    content = loader.render_to_string(
        template_name, {**c, **context}, request, using=using
    )
    resp = HttpResponse(content, content_type, status)

    # remove flash success cookie
    resp.set_cookie(SUCCESS_COOKIE_KEY)
    resp.set_cookie(ERROR_COOKIE_KEY)

    return resp


@lru_cache()
def is_valid_email(email) -> bool:
    if len(email) <= 3:
        return False
    email_regex = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"
    return bool(re.search(email_regex, email))


def random_str(length):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def create_credentials() -> str:
    # return bcrypt.hashpw(bytes(random_str(CREDENTIAL_LEN), encoding='utf8'), bcrypt.gensalt()).decode()
    return random_str(CREDENTIAL_LEN)


@lru_cache()
def kb_to_b(kb: int) -> int:
    return kb * 1024

import logging
import os
import random
import re
import string
from functools import lru_cache
from zipfile import ZipFile, ZipInfo

from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from rq import Queue

from idmyteam.structs import StoreImageJob
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
            "keywords": "detect, recognise, facial, recognition-worker, facial recognition-worker, detection, team, id, recogniser, ID My Team, idmy.team",
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


@lru_cache(maxsize=32)
def is_valid_email(email) -> bool:
    if len(email) <= 3:
        return False
    email_regex = "^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$"
    return bool(re.search(email_regex, email))


def random_str(length):
    return "".join(
        random.choice(string.ascii_letters + string.digits) for _ in range(length)
    )


def create_credentials() -> (str, str):
    # return bcrypt.hashpw(bytes(random_str(CREDENTIAL_LEN), encoding='utf8'), bcrypt.gensalt()).decode()
    return random_str(CREDENTIAL_LEN)


def kb_to_b(kb: int) -> int:
    return kb * 1024


class TeamTrainingImages:
    _images = {}

    def __init__(self, z: ZipFile, max_img_size_kb: int):
        self.z = z
        for file in z.infolist():
            if file.file_size:
                if file.file_size > kb_to_b(max_img_size_kb):
                    raise Exception(f"Training image '{file.filename}' is too large!")

                # get member from file structure
                try:
                    # members images expected to be put in separate directories
                    member = int(os.path.dirname(file.filename))
                except Exception as e:
                    logging.error(e)
                    logging.error("Invalid named file uploaded")
                    continue

                self._add(member, file)

    def __len__(self):
        return len(self._images)

    def _add(self, member: int, file: ZipInfo):
        if member in self._images:
            self._images[member].append(file)
        else:
            self._images[member] = [file]

    def crop(self, num):
        """
        extract a cropped amount of the team training images
        @param num:
        @return:
        """
        cropped_images = {}
        each, rem = divmod(num, len(self._images))
        for i, member in enumerate(self._images):
            if i < rem:
                cropped_images[member] = self._images[member][: each + 1]
            else:
                cropped_images[member] = self._images[member][:each]
        self._images = cropped_images

    def train(self, queue: Queue, team_username: str):
        for member in self._images:
            for file in self._images[member]:
                img: bytes = self.z.read(file)

                queue.enqueue_call(
                    func=".",
                    kwargs=StoreImageJob(
                        img=img,
                        file_name=file.filename,
                        team_username=team_username,
                        member_id=member,
                    ).dict(),
                )

        # tell model to now train
        queue.enqueue_call(
            func=".", kwargs={"type": "train", "team_username": team_username}
        )

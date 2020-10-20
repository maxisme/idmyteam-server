import logging
import os
import random
import re
import string
from functools import lru_cache
from zipfile import ZipFile

from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from rq import Queue

from idmyteam.structs import StoreImageJob, TrainJob
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


def create_credentials() -> str:
    # return bcrypt.hashpw(bytes(random_str(CREDENTIAL_LEN), encoding='utf8'), bcrypt.gensalt()).decode()
    return random_str(CREDENTIAL_LEN)


def kb_to_b(kb: int) -> int:
    return kb * 1024


class ZipImg:
    def __init__(self, name: str, img: bytes):
        self.name = name
        self.img = img


class TeamTrainingZip:
    def __init__(
        self,
        z: ZipFile,
        num_images_allowed_to_train: int,
        max_team_member_size: int,
        max_img_size_kb: int,
    ):
        self._imgs = {}
        members = set()
        img_cnt = 0
        for file in z.infolist():
            if file.file_size:
                img_cnt += 1
                if img_cnt > num_images_allowed_to_train:
                    logging.info("Too many images uploaded")
                    break

                if file.file_size > kb_to_b(max_img_size_kb):
                    raise Exception(f"Training image '{file.filename}' is too large!")

                # get member from file structure
                try:
                    # members images expected to be put in separate directories
                    member = self._extract_member_from_file_path(file.filename)
                except ValueError:
                    logging.error("Invalid named file uploaded")
                    continue
                members.add(member)
                if len(members) > max_team_member_size:
                    raise Exception(
                        f"You can't train more than {max_team_member_size} members!"
                    )
                self._add(member, ZipImg(name=file.filename, img=z.read(file)))

        if len(members) == 0:
            raise Exception(f"No members passed!")

    @staticmethod
    def _extract_member_from_file_path(path: str) -> int:
        # members images expected to be put in separate directories
        return int(os.path.basename(os.path.normpath(os.path.dirname(path))))

    def __len__(self):
        return len(self._imgs)

    def _add(self, member: int, file: ZipImg):
        if member in self._imgs:
            self._imgs[member].append(file)
        else:
            self._imgs[member] = [file]

    def enqueue(self, queue: Queue, team_username: str):
        for member in self._imgs:
            img: ZipImg
            for img in self._imgs[member]:
                queue.enqueue_call(
                    func=".",
                    kwargs=StoreImageJob(
                        img=img.img,
                        file_name=img.name,
                        team_username=team_username,
                        member_id=member,
                    ).dict(),
                )

        # tell model to now train
        queue.enqueue_call(
            func=".",
            kwargs=TrainJob(
                team_username=team_username,
            ).dict(),
        )

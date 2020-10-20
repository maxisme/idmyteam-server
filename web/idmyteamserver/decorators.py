from functools import wraps

from django.http import HttpResponseBadRequest, HttpResponseForbidden

from idmyteamserver.forms import UploadFileForm
from idmyteamserver.models import Team


def file_upload_auth_decorator():
    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            form = UploadFileForm(request.POST, request.FILES)
            if not form.is_valid():
                return HttpResponseBadRequest(form.errors)

            team = Team.objects.get(username=form.cleaned_data.get("username"))
            if not team.validate_credentials(form.cleaned_data.get("credentials")):
                return HttpResponseForbidden()  # TODO prevent brute force
            request.user = team
            return func(request, form, *args, **kwargs)

        return inner

    return decorator

from idmyteamserver.helpers import redirect
from idmyteamserver.models import Account
from web.settings import CREDENTIAL_LEN
from idmyteamserver import helpers


def delete_model_handler(request):
    user: Account = request.user
    if user.is_authenticated:
        pass # TODO


def delete_account_handler(request):
    user: Account = request.user
    if user.is_authenticated:
        pass # TODO


def toggle_storage_handler(request):
    user: Account = request.user
    if user.is_authenticated:
        user.allow_image_storage = False if user.allow_image_storage else True
        user.save()
    return redirect('/profile')


def reset_credentials_handler(request):
    user: Account = request.user
    if user.is_authenticated:
        user.credentials = helpers.random_str(CREDENTIAL_LEN)
        user.save()
    return redirect('/profile')

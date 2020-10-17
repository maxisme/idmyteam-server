from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV2Invisible
from django import forms
from django.forms import ModelForm

from idmyteamserver.models import Team
from web import settings


class RecaptchaForm(forms.Form):
    class CustomCaptcha(ReCaptchaField):
        widget = ReCaptchaV2Invisible

        def validate(self, value):
            # only validate if there is a private_key
            if self.private_key:
                super().validate(value)

    captcha = CustomCaptcha()


class SignUpForm(RecaptchaForm, ModelForm):
    password = forms.CharField(
        min_length=8, widget=forms.PasswordInput(), required=True, label="Password"
    )
    confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(),
        required=True,
        label="Confirm Password",
    )
    allow_image_storage = forms.BooleanField(
        label="Allow us to store images for <a href='/storage'>increased accuracy over time</a>",
        required=False,
        widget=forms.CheckboxInput(attrs={"id": "allow_image_storage"}),
    )
    terms = forms.BooleanField(
        label="Accept <a href='/terms'>Terms & Conditions</a>",
        required=True,
        widget=forms.CheckboxInput(attrs={"id": "terms"}),
    )

    class Meta:
        model = Team
        fields = [
            "username",
            "password",
            "confirm",
            "email",
            "allow_image_storage",
            "terms",
        ]

    def clean(self):
        cleaned_data = super(SignUpForm, self).clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm")

        if password != confirm:
            raise forms.ValidationError("Passwords do not match!")


class LoginForm(RecaptchaForm):
    username = forms.CharField(required=True, label="Username")
    password = forms.CharField(
        min_length=8, widget=forms.PasswordInput(), required=True, label="Password"
    )

    class Meta:
        fields = ["username", "password"]


class ForgotForm(RecaptchaForm):
    username_email = forms.CharField(label="Username or email")


class ResetForm(RecaptchaForm):
    reset_key = forms.CharField(widget=forms.HiddenInput())
    password = forms.CharField(
        min_length=8, widget=forms.PasswordInput(), required=True, label="Password"
    )
    confirm = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(),
        required=True,
        label="Confirm Password",
    )


class UploadFileForm(forms.Form):
    username = forms.CharField(required=True, label="Username")
    credentials = forms.CharField(
        min_length=settings.CREDENTIAL_LEN,
        max_length=settings.CREDENTIAL_LEN,
        widget=forms.PasswordInput(),
        required=True,
        label="Credentials",
    )
    store_image_features = forms.BooleanField()
    file = forms.FileField(max_length=settings.MAX_UPLOAD_SIZE, allow_empty_file=False)

    class Meta:
        model = Team


# class CustomForm(Form):
#     def __init__(self, *args, **kwargs):
#         args = self.SimpleMultiDict(*args)
#         super(CustomForm, self).__init__(args, **kwargs)
#
#     def validate(self):
#         status = super(CustomForm, self).validate()
#         for field in self._fields:
#             f = self._fields[field]
#             if f.errors:
#                 if not f.render_kw:
#                     f.render_kw = {}
#                 if "class" in f.render_kw:
#                     f.render_kw["class"] += " invalid"
#                 else:
#                     f.render_kw["class"] = "invalid"
#         return status
#
#     class SimpleMultiDict(dict):
#         def getlist(self, key):
#             arr = []
#             for k in self[key]:
#                 arr.append(k.decode("utf-8"))
#             return arr
#
#         def __repr__(self):
#             return type(self).__name__ + "(" + dict.__repr__(self) + ")"
#
#
# class LoginForm(CustomForm):
#     username = StringField("Username", [validators.InputRequired()], render_kw={"col": "m6 s12"})
#     password = PasswordField("Password", [validators.InputRequired()], render_kw={"col": "m6 s12"})
#     recaptcha = HiddenField(_name="g-recaptcha-response")
#
#
# class SignUpForm(CustomForm):
#     username = StringField(
#         "Username", [validators.Length(min=4), validators.InputRequired()]
#     )
#     password = PasswordField(
#         "Password",
#         [
#             validators.InputRequired(),
#             validators.Length(min=8),
#             validators.EqualTo("confirm", message="Passwords must match"),
#         ],
#         render_kw={"col": "m6 s12"},
#     )
#     confirm = PasswordField("Confirm Password", render_kw={"col": "m6 s12"})
#     email = EmailField("Email", [validators.InputRequired()])
#     store = BooleanField(
#         "Allow us to store images for <a href='/storage'>increased accuracy over time</a>",
#         render_kw={"col": "s12"},
#     )
#     TS_MESSAGE = "You must accept our Terms & Conditions!"
#     ts = BooleanField(
#         "Accept <a href='/terms'>Terms & Conditions</a>",
#         [validators.DataRequired(TS_MESSAGE)],
#         render_kw={"col": "s12"},
#     )
#     recaptcha = HiddenField(_name="g-recaptcha-response")
#
#
# class ForgotForm(CustomForm):
#     username = StringField("Username", render_kw={"col": "m6 s12"})
#     email = EmailField("Email", render_kw={"col": "m6 s12"})
#
#
# class ResetPasswordForm(CustomForm):
#     password = PasswordField(
#         "Password",
#         [
#             validators.InputRequired(),
#             validators.Length(min=8),
#             validators.EqualTo("confirm", message="Passwords must match!"),
#         ],
#         render_kw={"col": "m6 s12"},
#     )
#     confirm = PasswordField("Confirm Password", render_kw={"col": "m6 s12"})
#     token = HiddenField("Token", [validators.InputRequired()])
#     email = HiddenField()
#     username = HiddenField()
#     recaptcha = HiddenField(_name="g-recaptcha-response")

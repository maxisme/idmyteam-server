from django import forms
from django.forms import ModelForm
from models import User
from captcha.fields import ReCaptchaField


class LoginForm(ModelForm):
    captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ['username', 'password']


class SignUpForm(ModelForm):
    confirm_password = forms.CharField(min_length=8, widget=forms.PasswordInput(), required=True)
    terms = forms.BooleanField(required=True)
    captcha = ReCaptchaField()

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'allow_storage']

    def clean(self):
        cleaned_data = super(SignUpForm, self).clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password != confirm_password:
            raise forms.ValidationError(
                "password and confirm_password does not match"
            )

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
from wtforms import (
    Form,
    PasswordField,
    StringField,
    validators,
    BooleanField,
    HiddenField,
)
from wtforms.fields.html5 import EmailField


class CustomForm(Form):
    def __init__(self, *args, **kwargs):
        args = self.SimpleMultiDict(*args)
        super(CustomForm, self).__init__(args, **kwargs)

    def validate(self):
        status = super(CustomForm, self).validate()
        for field in self._fields:
            f = self._fields[field]
            if f.errors:
                if not f.render_kw:
                    f.render_kw = {}
                if "class" in f.render_kw:
                    f.render_kw["class"] += " invalid"
                else:
                    f.render_kw["class"] = "invalid"
        return status

    class SimpleMultiDict(dict):
        def getlist(self, key):
            arr = []
            for k in self[key]:
                arr.append(k.decode("utf-8"))
            return arr

        def __repr__(self):
            return type(self).__name__ + "(" + dict.__repr__(self) + ")"


class LoginForm(CustomForm):
    username = StringField("Username", [validators.InputRequired()])
    password = PasswordField("Password", [validators.InputRequired()])


class SignUpForm(CustomForm):
    username = StringField(
        "Username", [validators.Length(min=4), validators.InputRequired()]
    )
    password = PasswordField(
        "Password",
        [
            validators.InputRequired(),
            validators.Length(min=8),
            validators.EqualTo("confirm", message="Passwords must match"),
        ],
        render_kw={"col": "m6 s12"},
    )
    confirm = PasswordField("Confirm Password", render_kw={"col": "m6 s12"})
    email = EmailField("Email", [validators.InputRequired()])
    store = BooleanField(
        "Allow us to Store Images for <a href='/store'>increased accuracy over time</a>", render_kw={"col": "s12"}
    )
    TS_MESSAGE = "You must accept our Terms & Conditions!"
    ts = BooleanField(
        "<a href='/terms'>Terms & Conditions</a>",
        [validators.DataRequired(TS_MESSAGE)],
        render_kw={"col": "s12"},
    )


class ForgotForm(CustomForm):
    username = StringField("Username", render_kw={"col": "m6 s12"})
    email = EmailField("Email", render_kw={"col": "m6 s12"})


class ResetPasswordForm(CustomForm):
    password = PasswordField(
        "Password",
        [
            validators.InputRequired(),
            validators.Length(min=8),
            validators.EqualTo("confirm", message="Passwords must match!"),
        ],
        render_kw={"col": "m6 s12"},
    )
    confirm = PasswordField("Confirm Password", render_kw={"col": "m6 s12"})
    token = HiddenField("Token", [validators.InputRequired()])
    email = HiddenField()
    username = HiddenField()

from wtforms import Form, PasswordField, StringField, validators, BooleanField
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
                if 'class' in f.render_kw:
                    f.render_kw['class'] += ' invalid'
                else:
                    f.render_kw['class'] = 'invalid'
        return status

    class SimpleMultiDict(dict):
        def getlist(self, key):
            arr = []
            for k in self[key]:
                arr.append(k.decode('utf-8'))
            return arr

        def __repr__(self):
            return type(self).__name__ + '(' + dict.__repr__(self) + ')'


class LoginForm(CustomForm):
    username = StringField("Username", [validators.InputRequired()])
    password = PasswordField("Password", [validators.InputRequired()])


class SignUpForm(CustomForm):
    username = StringField("Username", [validators.Length(min=4), validators.InputRequired()])
    password = PasswordField("Password", [
        validators.InputRequired(),
        validators.Length(min=8),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')
    email = EmailField("Email", [
        validators.InputRequired()
    ])
    store = BooleanField("<a href='/store'>Store Images</a>", render_kw={
        'class': 'filled-in'
    })
    ts = BooleanField("<a href='/terms'>Terms & Conditions</a>", [
        validators.DataRequired("You must accept our Terms & Conditions!")
    ])

import os

from tornado import template

from settings import functions, config
conn = functions.connect(config.DB["username"], config.DB["password"], config.DB["db"])
functions.Team.ConfirmEmail.send_confirmation(conn, 'max@max.me.uk', 'maxisme', config.EMAIL_CONFIG)


# from premailer import transform
# loader = template.Loader("../web/")
# email_html = loader.load("templates/helpers/confirm-email.html").generate(email='foo', secret='bar')
# print(transform(email_html.decode()))
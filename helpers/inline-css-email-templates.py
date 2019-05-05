import os
from premailer import transform
from urllib.parse import unquote

html_head = '''
<head>
    <style>
        {}
    </style>
</head>
'''.format(open('../web/static/css/email.css', 'r').read())

email_dir = '../web/templates/emails/'
for filename in os.listdir(email_dir):
    path = email_dir + filename
    if os.path.isfile(path):
        print(path)
        file_content = open(path, 'r').read()
        inline_html = unquote(transform(html_head+file_content))
        f = open(path.replace('emails/','emails/inline/'), "w")
        f.write(inline_html)
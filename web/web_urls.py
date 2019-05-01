import view, authed, events

www_urls = [
    (r'/', view.WelcomeHandler),
    (r'/about', view.AboutHandler),
    (r'/contact', view.ContactHandler),
    (r'/terms', view.TermsHandler),

    (r'/tutorials', view.TutorialListHandler),
    (r'/tutorials/([A-Za-z0-9\-\_]+)', view.TutorialHandler),

    (r'/login', authed.LoginHandler),
    (r'/signup', authed.SignUpHandler),
    (r'/profile', authed.ProfileHandler),

    (r'/logout', events.LogoutHandler),
    (r'/delete-model', events.DeleteModelHandler),
    (r'/delete-account', events.DeleteAccountHandler),
    (r'/toggle-storage', events.AllowUploadStorageHandler),

    (r'/socket', authed.WebSocketHandler),
    (r'/local', authed.LocalWebSocketHandler),
    (r'/upload', authed.ImageUploadHandler),

    (r'/confirm', events.ConfirmEmail),
    (r'/resend', events.ResendConfirmationEmail),
]
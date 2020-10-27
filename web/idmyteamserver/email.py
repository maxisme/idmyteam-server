from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template

FROM_EMAIL = "noreply@idmy.team"


def send_confirm(request, to: str, key: str):
    template = get_template("emails/confirm.html")
    confirm_link = request.build_absolute_uri(f"/confirm/{key}") + f"?email={to}"
    _send_email(
        to=to,
        subject="Confirm account",
        html_content=template.render({"confirm_link": confirm_link}),
        text_content=f"Confirm your email address: {confirm_link}",
    )


def send_reset(request, to: str, key: str):
    template = get_template("emails/reset.html")
    reset_link = request.build_absolute_uri(f"/reset?key={key}")
    _send_email(
        to=to,
        subject="Reset password",
        html_content=template.render({"reset_link": reset_link}),
        text_content=f"Reset password: {reset_link}",
    )


def _send_email(
    to: str, subject: str, html_content: str, text_content: str
):  # pragma: no cover
    msg = EmailMultiAlternatives(subject, text_content, FROM_EMAIL, [to])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

from .client import ses_client
from .utils import render_template
import os

DEFAULT_SENDER = os.getenv("EMAIL_FROM", None)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)

def send_email(subject: str, to_email: str, html_body: str, text_body: str = ""):
    """Send an email using Amazon SES"""
    # silently drop if no sender configured
    if not DEFAULT_SENDER or not AWS_ACCESS_KEY or not AWS_SECRET_ACCESS_KEY:
        return None
    response = ses_client.send_email(
        Source=DEFAULT_SENDER,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject, "Charset": "UTF-8"},
            "Body": {
                "Html": {"Data": html_body, "Charset": "UTF-8"},
                "Text": {"Data": text_body or "Please view in HTML", "Charset": "UTF-8"},
            },
        },
    )
    return response

def send_welcome_email(to_email: str, first_name: str):
    subject = "Welcome to Statement!"
    html_body = render_template("welcome.html", user_email=to_email, first_name=first_name)
    return send_email(subject, to_email, html_body)

def send_verification_email(to_email: str, first_name: str, verify_link: str):
    subject = "Verify Your Email for Statement"
    html_body = render_template("verify_email.html", first_name=first_name, verify_link=verify_link)
    return send_email(subject, to_email, html_body)

def send_password_reset_email(to_email: str, first_name: str, reset_link: str):
    subject = "Reset Your Statement Password"
    html_body = render_template("reset_password.html", first_name=first_name, reset_link=reset_link)
    return send_email(subject, to_email, html_body)

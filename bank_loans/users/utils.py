from django.template.loader import render_to_string
from django.utils.translation import gettext as _


def get_first_matching_attr(obj, *attrs, default=None):
    for attr in attrs:
        if hasattr(obj, attr):
            return getattr(obj, attr)

    return default


def get_error_message(exc) -> str:
    if hasattr(exc, "message_dict"):
        return exc.message_dict
    error_msg = get_first_matching_attr(exc, "message", "messages")

    if isinstance(error_msg, list):
        error_msg = ", ".join(error_msg)

    if error_msg is None:
        error_msg = str(exc)

    return error_msg


def create_html_message(code, subject, message_text, footer_text):
    context = {
        "header_title": subject,
        "code": code,
        "message": message_text.replace("\n", "<br>"),
        "footer_text": footer_text,
    }
    return render_to_string("emails/user-auth-base.html", context)


def create_html_verify_email_message(code):
    message = _(
        "Please use the code below to confirm your email address and complete your registration."
    )
    footer = _(
        "If you didn't request this confirmation code, you can ignore this email. "
        "Someone else might have entered your email address by mistake."
    )
    return create_html_message(
        code,
        _("Confirm Your Email"),
        message,
        footer,
    )


def create_html_reset_password_message(code):
    message = _("Please use the code below to reset your password.")
    footer = _(
        "If you didn't request a password reset, you can ignore this email. "
        "Someone else might have entered your email address by mistake."
    )
    return create_html_message(
        code,
        _("Reset Your Password"),
        message,
        footer,
    )

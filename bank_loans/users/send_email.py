from django.conf import settings
from django.core.mail import send_mail


def send_email(subject: str, message: str, receiver, html_message: str = None):
    if isinstance(receiver, str):
        receiver = [receiver]
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.EMAIL_HOST_USER,
        recipient_list=receiver,
        fail_silently=False,
        html_message=html_message,
    )

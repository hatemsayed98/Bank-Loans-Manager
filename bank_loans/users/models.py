import random
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import EmailValidator
from django.db.models import CharField, DateTimeField, EmailField, BooleanField
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from bank_loans.users.send_email import send_email

from .utils import (
    create_html_reset_password_message,
    create_html_verify_email_message,
)
from .exceptions import ValidationError, WrongConfirmationCode


class User(AbstractUser):
    """
    Default custom user model for Bank Loans.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    ROLE_PROVIDER = "provider"
    ROLE_CUSTOMER = "customer"
    ROLE_BANK_PERSONNEL = "bank_personnel"

    ROLE_CHOICES = (
        (ROLE_PROVIDER, "Loan Provider"),
        (ROLE_CUSTOMER, "Loan Customer"),
        (ROLE_BANK_PERSONNEL, "Bank Personnel"),
    )

    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]
    role = CharField(max_length=15, choices=ROLE_CHOICES)
    email = EmailField(
        validators=[EmailValidator(message="Enter a valid email address.")], unique=True
    )
    email_verified = BooleanField(default=False)
    confirmation_code = CharField(max_length=4, blank=True, null=True)
    last_email_sent = DateTimeField(null=True, blank=True)
    password_reset_token = CharField(
        _("Password reset token"), blank=True, null=True, default=None, max_length=255
    )
    password_reset_token_sent_at = DateTimeField(
        verbose_name=_("token sent at"), default=None, null=True, blank=True
    )

    def send_confirmation_code(self):
        if not self.email_verified:
            if self.last_email_sent:
                difference = timezone.now() - self.last_email_sent
                seconds = difference.total_seconds()
                if seconds < settings.OTP_EXPIRATION_TIME:
                    remaining_seconds = int(settings.OTP_EXPIRATION_TIME - seconds)
                    time_format = (
                        f"{remaining_seconds // 60:02}:{remaining_seconds % 60:02}"
                    )

                    raise ValidationError(
                        {
                            "non_field_errors": [
                                _(
                                    "You have to wait at least {time} before requesting another code."
                                ).format(time=time_format)
                            ],
                            "seconds": remaining_seconds,
                        }
                    )
            confirmation_code = f"{random.randint(0, 9999):04d}"
            self.confirmation_code = confirmation_code

            email_html_content = create_html_verify_email_message(confirmation_code)
            send_email(
                subject=_("Confirm Your Email"),
                message=email_html_content,
                html_message=email_html_content,
                receiver=self.email,
            )

            self.last_email_sent = timezone.now()
            self.save()

    def confirm_email(self, code):
        if code == self.confirmation_code:
            self.email_verified = True
            self.confirmation_code = None
            self.last_email_sent = None
            self.save()
        else:
            raise WrongConfirmationCode(_("Wrong or expired confirmation code"))

    def send_reset_password_code(self):
        if self.password_reset_token and self.password_reset_token_sent_at:
            difference = timezone.now() - self.password_reset_token_sent_at
            seconds = difference.total_seconds()
            if seconds < settings.OTP_EXPIRATION_TIME:
                remaining_seconds = int(settings.OTP_EXPIRATION_TIME - seconds)
                time_format = (
                    f"{remaining_seconds // 60:02}:{remaining_seconds % 60:02}"
                )

                raise ValidationError(
                    {
                        "non_field_errors": [
                            _(
                                "You have to wait at least {time} before requesting another code."
                            ).format(time=time_format)
                        ],
                        "seconds": remaining_seconds,
                    }
                )
        reset_code = f"{random.randint(0, 9999):04d}"
        self.password_reset_token = reset_code

        email_html_content = create_html_reset_password_message(reset_code)
        send_email(
            subject=_("Reset Password"),
            message=email_html_content,
            html_message=email_html_content,
            receiver=self.email,
        )

        self.password_reset_token_sent_at = timezone.now()
        self.save()

    def apply_password_reset(self, code, password):
        if code == self.password_reset_token:
            if self.check_password(password):
                raise ValidationError(
                    _("The new password is the same as the current password.")
                )
            self.set_password(password)
            self.password_reset_token = None
            self.password_reset_token_sent_at = None
            self.save()
        else:
            raise WrongConfirmationCode(_("Wrong or expired code"))

    @property
    def latest_plan(self):
        """
        Return the most recent non-expired plan or a default free plan.
        """
        recent_subscription = (
            self.subscription_user.order_by("-start_date")
            .filter(end_date__gt=timezone.now())
            .first()
        )
        return recent_subscription.plan

from django import forms
from django.contrib.auth import forms as admin_forms
from django.forms import EmailField
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    email_verified = forms.BooleanField(
        label=_("Email Verified"),
        required=False,
        help_text=_("Check this box if the user has verified their email."),
    )

    class Meta(admin_forms.UserChangeForm.Meta):
        model = User
        field_classes = {"email": EmailField}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["email_verified"].initial = (
                self.instance.email_verified is not None
            )

    def save(self, commit=True):
        if self.cleaned_data["email_verified"] and not self.instance.email_verified:
            self.instance.email_verified = True
        elif not self.cleaned_data["email_verified"]:
            self.instance.email_verified = False
        return super().save(commit=commit)


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):
        model = User
        fields = (
            "email",
            "username",
        )
        field_classes = {"email": EmailField}
        error_messages = {
            "email": {"unique": _("This email has already been taken.")},
            "username": {"unique": _("This username has already been taken.")},
        }

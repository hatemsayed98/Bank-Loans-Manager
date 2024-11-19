from django.urls import path

from .api.views import (
    CheckConfirmationCodeView,
    ConfirmEmailView,
    PasswordResetTokenObtainView,
    RegisterView,
    ResendConfirmationCodeView,
    ResetPasswordView,
    SignInView,
    LogoutView,
    UpdateProfileView,
    UserRetrieveView,
)

app_name = "users"
urlpatterns = [
    path("login/", SignInView.as_view(), name="token-obtain-pair"),
    path("profile/", UserRetrieveView.as_view(), name="profile"),
    path("update-profile/", UpdateProfileView.as_view(), name="update-profile"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("register/", RegisterView.as_view(), name="register"),
    path(
        "resend-confirmation-code/",
        ResendConfirmationCodeView.as_view(),
        name="resend-confirmation-code",
    ),
    path("confirm-email/", ConfirmEmailView.as_view(), name="confirm-email"),
    path(
        "send-reset-password-code/",
        PasswordResetTokenObtainView.as_view(),
        name="send-password-reset-url",
    ),
    path(
        "check-reset-password-code/",
        CheckConfirmationCodeView.as_view(),
        name="check-confirmation-code",
    ),
    path("password-reset-confirm/", ResetPasswordView.as_view(), name="password-reset"),
]

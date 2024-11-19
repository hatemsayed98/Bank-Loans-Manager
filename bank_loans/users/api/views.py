import time

from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.generics import RetrieveAPIView
from rest_framework.generics import DestroyAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from bank_loans.users.exceptions import ValidationError
from .serializers import (
    CheckConfirmationCodeSerializer,
    EmailConfirmationSerializer,
    EmailResendConfirmationSerializer,
    PasswordResetCodeSerializer,
    PasswordResetSerializer,
    SignInSerializer,
    UpdateProfileSerializer,
    UserDetailSerializer,
    UserRegistrationSerializer,
)

User = get_user_model()


class UserRetrieveView(RetrieveAPIView):
    serializer_class = UserDetailSerializer
    queryset = User.objects.all()

    def get_object(self):
        return self.request.user


class SignInView(ObtainAuthToken):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = SignInSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        user_serializer = UserDetailSerializer(user)

        return Response({"token": token.key, "user": user_serializer.data})


class UpdateProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UpdateProfileSerializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            UserDetailSerializer(user).data,
            status=status.HTTP_200_OK,
        )


class LogoutView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        request.auth.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.send_confirmation_code()
        return Response({"is_ok": True}, status=status.HTTP_201_CREATED)


class ResendConfirmationCodeView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request, *args, **kwargs):
        serializer = EmailResendConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")

        user = User.objects.filter(email=email).first()

        if user and not user.email_verified:
            user.send_confirmation_code()
        else:
            time.sleep(4)

        return Response({"is_ok": True}, status=status.HTTP_200_OK)


class CheckConfirmationCodeView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = CheckConfirmationCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        confirmation_code = serializer.validated_data["confirmation_code"]

        try:
            User.objects.get(email=email, password_reset_token=confirmation_code)
            return Response({"is_ok": True}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"non_field_errors": [_("Invalid confirmation code or email.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ConfirmEmailView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = EmailConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")
        confirmation_code = serializer.validated_data.get("confirmation_code")
        try:
            user = User.objects.get(email=email, confirmation_code=confirmation_code)
            user.confirm_email(confirmation_code)
            return Response({"is_ok": True}, status=status.HTTP_200_OK)
        except (Exception, ValidationError) as e:
            print(e)
            return Response(
                {"non_field_errors": [_("Invalid confirmation code or email.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )


class PasswordResetTokenObtainView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data.get("email")

        user = User.objects.filter(email=email).first()

        if user:
            user.send_reset_password_code()
        else:
            time.sleep(4)

        return Response({"is_ok": True}, status=status.HTTP_200_OK)


class ResetPasswordView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        confirmation_code = serializer.validated_data["confirmation_code"]

        password = serializer.validated_data.get("password")
        try:
            user = User.objects.get(email=email, password_reset_token=confirmation_code)
            user.apply_password_reset(confirmation_code, password)
            return Response({"is_ok": True}, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response(
                {"non_field_errors": [_("Invalid confirmation code or email.")]},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            return Response(
                {"non_field_errors": [str(e)]}, status=status.HTTP_400_BAD_REQUEST
            )

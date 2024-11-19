from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator


User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    name = serializers.CharField(
        allow_blank=False,
        required=True,
        min_length=3,
        max_length=50,
    )

    username = serializers.CharField(
        allow_blank=False,
        required=True,
        min_length=3,
        max_length=50,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message=_("This username is already in use."),
            )
        ],
    )

    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
        validators=[
            UniqueValidator(
                queryset=User.objects.all(), message=_("This email is already in use.")
            )
        ],
    )
    password = serializers.CharField(
        min_length=8,
        max_length=20,
        write_only=True,
        validators=[validate_password],
    )

    role = serializers.ChoiceField(
        choices=[User.ROLE_PROVIDER, User.ROLE_CUSTOMER],
        required=True,
        error_messages={
            "invalid_choice": _(
                f"Role must be either '{User.ROLE_PROVIDER}' or '{User.ROLE_CUSTOMER}'."
            )
        },
    )

    class Meta:
        model = User
        stop_on_first_error = True
        fields = ("name", "username", "email", "password", "role")

    def validate_name(self, value):
        if len(value.split()) < 2:
            raise serializers.ValidationError(
                _("Please enter both first and last name.")
            )
        return value

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class SignInSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")

        if username and password:
            user = authenticate(
                request=self.context.get("request"),
                username=username,
                password=password,
            )
            if user and not user.email_verified:
                raise serializers.ValidationError("Your email address is not verified.")
            if not user:
                raise serializers.ValidationError(
                    "Unable to log in with provided credentials."
                )
        else:
            raise serializers.ValidationError(
                "Unable to log in with provided credentials."
            )

        attrs["user"] = user
        return attrs


class UserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "email", "name", "role"]


class EmailConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
    )
    confirmation_code = serializers.CharField(
        max_length=4,
        required=True,
    )

    class Meta:
        stop_on_first_error = True
        fields = "email"


class EmailResendConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
    )

    class Meta:
        stop_on_first_error = True
        fields = "email"


class PasswordResetCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
    )

    class Meta:
        stop_on_first_error = True
        fields = "email"


class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
    )
    password = serializers.CharField(
        min_length=8,
        max_length=20,
        validators=[validate_password],
    )
    confirmation_code = serializers.CharField(
        max_length=4,
        required=True,
    )


class CheckConfirmationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(
        allow_blank=False,
        label="Email address",
        max_length=255,
        required=True,
    )
    confirmation_code = serializers.CharField(
        max_length=4,
        required=True,
    )


class UpdateProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name", "password"]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 8,
                "max_length": 20,
                "validators": [validate_password],
            }
        }

    def validate_name(self, value):
        if len(value.split()) < 2:
            raise serializers.ValidationError(
                _("Please enter both first and last name.")
            )
        return value

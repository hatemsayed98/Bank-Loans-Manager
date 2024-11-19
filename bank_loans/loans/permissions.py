from rest_framework.permissions import BasePermission
from django.contrib.auth import get_user_model

User = get_user_model()


class IsProvider(BasePermission):
    """
    Custom permission to only allow access to users with the 'provider' role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_PROVIDER


class IsCustomer(BasePermission):
    """
    Custom permission to only allow access to users with the 'customer' role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == User.ROLE_CUSTOMER


class IsBankPersonnel(BasePermission):
    """
    Custom permission to only allow access to users with the 'bank_personnel' role.
    """

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.ROLE_BANK_PERSONNEL
        )

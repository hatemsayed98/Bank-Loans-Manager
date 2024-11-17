from rest_framework.permissions import BasePermission


class IsProvider(BasePermission):
    """
    Custom permission to only allow access to users with the 'provider' role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "provider"


class IsCustomer(BasePermission):
    """
    Custom permission to only allow access to users with the 'customer' role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "customer"


class IsBankPersonnel(BasePermission):
    """
    Custom permission to only allow access to users with the 'bank_personnel' role.
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "bank_personnel"

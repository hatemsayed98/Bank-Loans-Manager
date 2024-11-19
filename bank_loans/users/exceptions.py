from rest_framework.exceptions import APIException


class ValidationError(APIException):
    status_code = 400


class AlreadyVerified(Exception):
    status_code = 400


class WrongConfirmationCode(Exception):
    status_code = 400

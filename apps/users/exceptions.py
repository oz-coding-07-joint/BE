from rest_framework.exceptions import APIException


class UserValidationError(APIException):
    status_code = 400
    default_detail = "잘못된 요청입니다."
    default_code = "invalid"

    def __init__(self, detail=None):
        if detail is None:
            detail = self.default_detail
        super().__init__({"error": detail})

from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        # 쿠키에서 액세스 토큰 가져오기
        access_token = request.COOKIES.get('access_token')

        if access_token:
            try:
                validated_token = self.get_validated_token(access_token)
                return self.get_user(validated_token), validated_token
            except Exception:
                pass  # 쿠키의 토큰이 유효하지 않으면 헤더 확인

        # 원래의 헤더 인증 방식도 사용
        return super().authenticate(request)
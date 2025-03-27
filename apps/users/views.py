import random
import smtplib
import uuid

import requests
from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.utils import redis_client
from config.settings.base import (
    EMAIL_HOST_USER,
    KAKAO_CLIENT_ID,
    KAKAO_REDIRECT_URI,
    KAKAO_SECRET,
)

from .authentications import AllowInactiveUserJWTAuthentication
from .models import Student, User
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    SendEmailVerificationCodeSerializer,
    SignupSerializer,
    SocialSignupSerializer,
    SocialUserSerializer,
    UpdateMyPageSerializer,
    UserSerializer,
    VerifyEmailCodeSerializer,
)


class RedisKeys:
    """
    Redis 관련 이메일 상수 클래스

    VERIFIED_EMAIL: 이미 인증된 이메일 cache
    EMAIL_VERIFICATION: 특정 이메일에 보낸 인증코드 cache
    EMAIL_REQUEST_LIMIT: 인증 요청을 이미 보낸 이메일 검증 cache
    KAKAO_ACCESS_TOKEN: 카카오에서 발급받은 엑세스 토큰 cache
    KAKAO_REFRESH_TOKEN: 카카오에서 발급받은 리프레시 토큰 cache
    """

    VERIFIED_EMAIL = "verified_email_{email}"
    EMAIL_VERIFICATION = "email_verification_{email}"
    EMAIL_REQUEST_LIMIT = "email_request_limit_{email}"
    KAKAO_ACCESS_TOKEN = "kakao_access_token_{provider_id}"
    KAKAO_REFRESH_TOKEN = "kakao_refresh_token_{provider_id}"

    @staticmethod
    def get_verified_email_key(email):
        return RedisKeys.VERIFIED_EMAIL.format(email=email)

    @staticmethod
    def get_email_verification_key(email):
        return RedisKeys.EMAIL_VERIFICATION.format(email=email)

    @staticmethod
    def get_email_request_limit_key(email):
        return RedisKeys.EMAIL_REQUEST_LIMIT.format(email=email)

    @staticmethod
    def get_kakao_access_token_key(provider_id):
        return RedisKeys.KAKAO_ACCESS_TOKEN.format(provider_id=provider_id)

    @staticmethod
    def get_kakao_refresh_token_key(provider_id):
        return RedisKeys.KAKAO_REFRESH_TOKEN.format(provider_id=provider_id)


class SendEmailVerificationCodeView(APIView):
    """
    이메일 인증 요청 보내는 API

    1. 이메일 인증 요청을 보낼 때 이미 가입된 이메일인지 확인
    2. 이미 인증이 완료된 이메일인지 확인
    3. EMAIL_REQUEST_LIMIT으로 이메일 요청 테러 방지(30초 제한)
    4. 이 이메일key를 가진 캐시된 코드가 있는지 확인
    5. 인증코드 전송
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="이메일 인증 요청",
        description="유저 이메일로 인증 번호를 보냅니다",
        request=SendEmailVerificationCodeSerializer,
        tags=["User"],
    )
    def post(self, request):
        email = request.data.get("email")

        if User.objects.filter(email=email, deleted_at__isnull=True).exists():
            return Response({"detail": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 인증된 이메일인지 확인
        if redis_client.get(RedisKeys.get_verified_email_key(email)):
            return Response({"error": "이미 인증이 완료된 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ttl(Time to Live) = 키에 설정된 만료 시간을 관리
        # 이미 인증을 요청한 경우 몇 초 이후에 다시 요청을 보낼 수 있는 지 알려줌(30초 시작)
        remaining_time = redis_client.ttl(RedisKeys.get_email_request_limit_key(email))
        if remaining_time > 0:
            return Response(
                {"error": f"이메일 인증 요청은 {remaining_time}초 후에 가능합니다."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # 기존 인증 코드가 있는지 확인
        existing_code = redis_client.get(RedisKeys.get_email_verification_key(email))

        # 기존 코드가 이미 있거나 만료되지 않은 경우
        if existing_code or not redis_client.ttl(RedisKeys.get_email_verification_key(email)) <= 0:
            return Response(
                {"message": "인증 코드가 이미 존재합니다. 기존 코드를 사용하세요."},
                status=status.HTTP_200_OK,
            )

        # 기존 코드가 캐시되어 있다면 삭제하는 로직(혹시 모르니까)
        redis_client.delete(RedisKeys.get_email_verification_key(email))

        # 6자리 랜덤 인증 코드 생성
        verification_code = str(random.randint(100000, 999999))

        # Redis에 인증 코드 저장 / [email_verification_key]가 저장되는 부분
        # ex=Expiration Time -> 만료시간 설정(300초)
        # nx=Not Exists -> 값이 존재하지 않으면 값을 설정
        success = redis_client.set(RedisKeys.get_email_verification_key(email), verification_code, ex=300, nx=True)
        # 만약 이미 코드가 존재했다면 기존 코드 사용
        if not success:
            verification_code = redis_client.get(RedisKeys.get_email_verification_key(email))

        # 이메일 테러를 방지하기 위해 Rate Limiting 적용 (30초 동안 재요청 불가)
        redis_client.setex(RedisKeys.get_email_request_limit_key(email), 30, "1")

        # 인증코드 전송
        try:
            send_mail(
                subject="소리상상 이메일 인증 코드입니다",
                message=f"당신의 이메일 인증 코드는 {verification_code} 입니다.",
                from_email=EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except smtplib.SMTPAuthenticationError:
            return Response(
                {"detail": "SMTP 인증 오류: 이메일과 비밀번호를 확인하세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            return Response(
                {"detail": "예상치 못한 오류가 발생했습니다."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {"message": "인증 코드가 이메일로 전송되었습니다. 5분 이내에 확인해주세요."}, status=status.HTTP_200_OK
        )


class VerifyEmailCodeView(APIView):
    """
    이메일 인증 확인하는 API

    1. 요청 이메일과 인증코드를 입력 받아옴
    2. 요청 이메일을 key로 가진 인증코드를 가져옴
    3. 인증이 성공되어 cache된 인증코드가 삭제된 상태일 때 400 error
    4. redis에서 가져온 데이트가 byte type일수도 있어서 decode
    5. 인증코드가 cache된 코드와 같은지 확인
    6. 인증코드가 올바르면 요청 이메일을 redis에 cache해서 회원가입 때 인증이 완료된 이메일인지 확인
    7. 사용된 인증코드는 삭제처리
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="이메일 인증 확인",
        description="인증 번호가 맞는지 확인합니다",
        request=VerifyEmailCodeSerializer,
        tags=["User"],
    )
    def post(self, request):
        email = request.data.get("email")
        input_code = request.data.get("code")

        # 저장된 인증 코드 가져오기
        stored_code = redis_client.get(RedisKeys.get_email_verification_key(email))

        # Redis에서 가져온 데이터가 None일 경우
        if stored_code is None:
            return Response(
                {
                    "error": "이미 이메일 인증에 성공하여 인증코드가 삭제된 상태입니다. 회원가입이 안되신다면 5분 후 다시 시도해주세요."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Redis에서 가져온 데이터가 bytes일 경우 decode 처리
        if isinstance(stored_code, bytes):
            stored_code = stored_code.decode()

        # Redis의 코드와 입력코드가 다른 경우
        if stored_code != input_code:
            return Response({"error": "잘못된 인증 코드입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 이메일 인증 완료 여부 저장 / [verified_email_key]가 저장되는 부분
        redis_client.setex(RedisKeys.get_verified_email_key(email), 300, "true")

        # 사용된 인증코드는 삭제
        redis_client.delete(RedisKeys.get_email_verification_key(email))

        return Response({"message": "이메일 인증이 완료되었습니다!"}, status=status.HTTP_200_OK)


class SignUpView(APIView):
    """
    회원가입 API
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="회원가입", description="회원정보를 입력받아 새 사용자를 생성", request=SignupSerializer, tags=["User"]
    )
    def post(self, request):
        email = request.data.get("email")

        if User.objects.filter(email=email, deleted_at__isnull=True).exists():
            return Response({"detail": "이미 존재하는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 이메일 인증 여부 확인
        is_verified = redis_client.get(RedisKeys.get_verified_email_key(email))

        if is_verified is None:
            return Response({"error": "이메일 인증이 완료되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 소프트 삭제된 유저인 경우 db 완전 삭제 후 다시 계정 생성
        if User.deleted_objects.filter(email=email).exists():
            deleted_user = User.deleted_objects.filter(email=email).first()
            deleted_user.hard_delete()

        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    user.refresh_from_db()  # db에 바로 적용이 안되어 id가 orm으로 안 가져와질 수 있으므로 refresh
                    if not Student.objects.filter(user=user).exists():
                        Student.objects.create(user=user)
                    redis_client.delete(RedisKeys.get_verified_email_key(email))

                return Response({"message": "회원가입 성공!"}, status=status.HTTP_201_CREATED)
            
            except IntegrityError:
                return Response({"error": "이미 사용 중인 닉네임 또는 전화번호 입니다."}, status=status.HTTP_400_BAD_REQUEST)

            except serializers.ValidationError as e:
                return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({"error": f"회원가입 중 오류 발생{e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    로그인 API
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="로그인", description="이메일과 비밀번호를 받아 로그인합니다", request=LoginSerializer, tags=["User"]
    )
    def post(self, request):
        email = request.data.get("email")
        if not email:
            return Response({"detail": "이메일을 입력하세요"}, status=status.HTTP_400_BAD_REQUEST)
        password = request.data.get("password")
        if not password:
            return Response({"detail": "비밀번호를 입력하세요"}, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(email=email, password=password)  # db에 유저가 있는지 검증

        if not User.objects.filter(email=email).exists():
            return Response({"detail": "존재하지 않는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not user:
            return Response({"error": "잘못된 비밀번호입니다."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        user_data = User.objects.get(email=email)
        serializer = UserSerializer(user_data)

        response = Response({"access": access_token, "user": serializer.data}, status=status.HTTP_200_OK)
        response.set_cookie(
            "refresh_token",  # 쿠키 이름
            value=str(refresh),  # 쿠키 값
            httponly=True,  # JavaScript에서 쿠키 접근을 막음
            secure=settings.REFRESH_TOKEN_COOKIE_SECURE,  # HTTPS 환경에서만 쿠키를 전송(dev[F], prod[T]로 관리)
            samesite="Lax",  # CSRF 공격 방지
            max_age=5 * 60 * 60,  # 쿠키 만료 시간 5시간
        )
        return response


class TokenRefreshView(APIView):
    """
    refresh 토큰을 받으면 기존의 refresh token은 blacklist 처리하고
    access와 refresh token을 발급해주는 API
    """

    permission_classes = (AllowAny,)
    authentication_classes = [AllowInactiveUserJWTAuthentication]

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"Refresh token이 제공되지 않았습니다."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            # 기존 리프레쉬 토큰 검증
            old_refresh = RefreshToken(refresh_token)
            user_id = old_refresh.payload.get("user_id")
            if not user_id:
                raise Exception("유저 정보가 존재하지 않습니다.")
            user = User.objects.get(id=user_id)

            # 기존 refresh token 블랙리스트 처리
            old_refresh.blacklist()

            # 새 refresh token 생성
            new_refresh = RefreshToken.for_user(user)
            new_access_token = str(new_refresh.access_token)

            # body 에 access token 만 포함한 응답 생성
            response = Response({"access": new_access_token}, status=status.HTTP_200_OK)

            # 새 refresh token 을 쿠키에 설정
            response.set_cookie(
                key="refresh_token",
                value=str(new_refresh),
                httponly=True,
                secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
                samesite="Lax",
                max_age=5 * 60 * 60,
            )
            return response
        except Exception:
            return Response({"detail": "잘못된 refresh token 입니다."}, status=status.HTTP_403_FORBIDDEN)


class LogoutView(APIView):
    """
    로그아웃 API
    """

    @extend_schema(
        summary="로그아웃", description="refresh token을 blacklist에 등록 후 로그아웃하는 API입니다", tags=["User"]
    )
    def post(self, request):

        # 소셜로그인 유저인지 확인 후 소셜 로그아웃 우선 진행
        if request.user.provider_id is not None:
            # 엑세스토큰 refresh 요청
            kakao_refresh_url = "https://kauth.kakao.com/oauth/token"
            data = {
                "grant_type": "refresh_token",
                "client_id": KAKAO_CLIENT_ID,
                "client_secret": KAKAO_SECRET,
                "refresh_token": redis_client.get(RedisKeys.get_kakao_refresh_token_key(request.user.provider_id)),
            }
            token_response = requests.post(kakao_refresh_url, data=data)
            if token_response.status_code != 200:
                return Response({"error": "카카오 토큰 재발급에 실패했습니다."}, status=status.HTTP_400_BAD_REQUEST)

            # 소셜로그인 유저 로그아웃 요청
            kakao_logout_url = "https://kapi.kakao.com/v1/user/logout"
            kakao_access_token = token_response.json()["access_token"]
            if kakao_access_token is None:
                return Response(
                    {"error": "kakao_access_token을 가져오지 못했습니다."}, status=status.HTTP_400_BAD_REQUEST
                )
            headers = {"Authorization": f"Bearer {kakao_access_token}"}
            logout_response = requests.post(url=kakao_logout_url, headers=headers)
            if logout_response.status_code != 200:
                return Response({"error": "카카오 로그아웃 요청에 실패했습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 일반 로그인 유저의 경우 여기서부터 진행
        # refresh token 블랙리스트 등록
        refresh_token = request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response({"Refresh token 이 제공되지 않았습니다."}, status=status.HTTP_401_UNAUTHORIZED)

        try:
            token = RefreshToken(refresh_token)
            token.blacklist()  # 로그아웃 시 refresh token을 블랙리스트에 등록
        except Exception:
            return Response({"에러발생, 관리자에게 문의해주세요"}, status=status.HTTP_400_BAD_REQUEST)

        response = Response({"detail": "로그아웃 되었습니다."}, status=status.HTTP_200_OK)
        response.delete_cookie("refresh_token")

        # 소셜로그인 캐시 정보 삭제
        redis_client.delete(RedisKeys.get_kakao_refresh_token_key(request.user.provider_id))
        redis_client.delete(RedisKeys.get_kakao_access_token_key(request.user.provider_id))

        return response


class WithdrawalView(APIView):
    """
    회원탈퇴 API
    """

    @extend_schema(summary="회원탈퇴", description="유저를 soft delete로 관리하는 회원탈퇴 API입니다", tags=["User"])
    def delete(self, request):
        user = request.user
        # 소셜 유저라면 소셜 로그인을 먼저 끊어주기 위한 if문
        if user.provider_id is not None:
            try:
                # 엑세스토큰 refresh 요청
                kakao_refresh_url = "https://kauth.kakao.com/oauth/token"
                data = {
                    "grant_type": "refresh_token",
                    "client_id": KAKAO_CLIENT_ID,
                    "client_secret": KAKAO_SECRET,
                    "refresh_token": redis_client.get(RedisKeys.get_kakao_refresh_token_key(request.user.provider_id)),
                }
                token_response = requests.post(kakao_refresh_url, data=data)
                if token_response.status_code != 200:
                    return Response({"error": "카카오 토큰 재발급에 실패했습니다."}, status=status.HTTP_400_BAD_REQUEST)

                # 카카오 연결 끊기
                unlink_url = "https://kapi.kakao.com/v1/user/unlink"
                kakao_access_token = token_response.json()["access_token"]
                headers = {"Authorization": f"Bearer {kakao_access_token}"}
                response = requests.post(unlink_url, headers=headers)
                if response.status_code != 200:
                    return Response({"error": "카카오 계정 연결 해제 실패"}, status=status.HTTP_400_BAD_REQUEST)

            except Exception:
                return Response(
                    {"error": "소셜 계정 연결 해제 중 오류 발생, 관리자에게 문의해주세요"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # 쿠키에서 refresh token 추출
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                return Response({"에러발생, 관리자에게 문의해주세요"}, status=status.HTTP_400_BAD_REQUEST)

        # soft delete 처리 (탈퇴 상태로 저장)
        user.is_active = False
        user.delete()

        # refresh token 삭제 후 응답 반환
        response = Response(
            {"detail": "회원 탈퇴가 완료되었습니다. 같은 이메일로 재가입해도 데이터는 남아있지 않습니다."},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie("refresh_token")
        # 소셜로그인 캐시 정보 삭제
        redis_client.delete(RedisKeys.get_kakao_refresh_token_key(request.user.provider_id))
        redis_client.delete(RedisKeys.get_kakao_access_token_key(request.user.provider_id))
        return response


class MyinfoView(APIView):
    """
    마이 페이지 API
    """

    @extend_schema(
        summary="회원 정보 조회",
        description="회원 정보를 조회하는 API입니다",
        responses={200, UserSerializer},
        tags=["User"],
    )
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="회원 정보 수정",
        description="회원 정보를 수정하는 API입니다",
        request=UpdateMyPageSerializer,
        tags=["User"],
    )
    def patch(self, request):
        user = request.user
        ori_user = User.objects.filter(id=user.pk).first()
        # 요청된 데이터 중 비교할 필드만 선택
        update_fields = {key: value for key, value in request.data.items() if key in ["email", "name", "phone_number"]}

        # 변경 사항 확인
        if all(getattr(ori_user, field) == update_fields[field] for field in update_fields):
            return Response({"error": "변경사항이 없습니다"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = UpdateMyPageSerializer(user, data=request.data, partial=True, context={"request": request})

        if serializer.is_valid():
            serializer.save()
            email = serializer.validated_data["email"]
            if email:
                redis_client.delete(RedisKeys.get_verified_email_key(email))
            return Response({"detail": "회원 정보 변경이 완료되었습니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    """
    비밀번호 변경 API
    """

    @extend_schema(
        summary="비밀번호 변경",
        description="비밀번호를 변경하는 API입니다",
        request=ChangePasswordSerializer,
        tags=["User"],
    )
    def patch(self, request):
        user = request.user
        serializer = ChangePasswordSerializer(data=request.data, context={"request": request})

        if serializer.is_valid():
            new_password = serializer.validated_data["new_password"]
            user.set_password(new_password)
            user.save()

            return Response({"detail": "비밀번호가 성공적으로 변경되었습니다."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class KakaoAuthView(APIView):
    """
    1. 카카오 인가 코드를 받아 액세스 토큰 요청
    2. 액세스 토큰으로 사용자 정보 조회
    3. 기존 가입된 유저인지 확인 후 JWT 발급 or 추가 정보 요청
    """

    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        summary="소셜 로그인",
        description="소셜 로그인을 위한 API입니다",
        request={"application/json": {"properties": {"code": {"type": "string"}}, "requrired": ["code"]}},
        tags=["User"],
    )
    def post(self, request):
        kakao_code = request.data.get("code")  # 프론트엔드에서 받은 인가 코드

        if not kakao_code:
            return Response({"error": "인가 코드가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 인가 코드로 카카오 액세스 토큰 요청
        kakao_token_url = "https://kauth.kakao.com/oauth/token"

        data = {
            "grant_type": "authorization_code",
            "client_id": KAKAO_CLIENT_ID,
            "client_secret": KAKAO_SECRET,
            "redirect_uri": KAKAO_REDIRECT_URI,
            "code": kakao_code,
        }

        token_response = requests.post(kakao_token_url, data=data)
        if token_response.status_code != 200:
            return Response({"error": "카카오 토큰 요청 실패"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            kakao_access_token = token_response.json().get("access_token")
            kakao_refresh_token = token_response.json().get("refresh_token")

        except Exception:
            return Response(
                {"error": "토큰 요청은 성공했으나 토큰을 받아오지 못했습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        # 액세스 토큰으로 카카오 사용자 정보 요청
        kakao_user_info_url = "https://kapi.kakao.com/v2/user/me"
        headers = {"Authorization": f"Bearer {kakao_access_token}"}
        user_info_response = requests.get(kakao_user_info_url, headers=headers)

        if user_info_response.status_code != 200:
            return Response({"error": "카카오 사용자 정보 요청 실패"}, status=status.HTTP_400_BAD_REQUEST)

        kakao_user_info = user_info_response.json()
        kakao_id = kakao_user_info.get("id")

        if not kakao_id:
            return Response({"error": "provider_id가 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 소프트 삭제된 유저인 경우 db 완전 삭제 후 다시 계정 생성
        if User.deleted_objects.filter(provider_id=kakao_id).exists():
            deleted_user = User.deleted_objects.filter(provider_id=kakao_id).first()
            deleted_user.hard_delete()

        # 기존 가입된 유저인지 확인
        user = User.objects.filter(provider_id=kakao_id).first()

        if not user:
            # 신규 가입 유저 → 추가 정보 입력 필요
            user = User.objects.create(
                email=f"{kakao_id}@kakao.com",
                provider="KAKAO",
                provider_id=kakao_id,
                is_active=False,
                nickname=uuid.uuid4().hex[:20],
                phone_number=uuid.uuid4().hex[:20],
            )
            user.set_unusable_password()
            user.save()

        user.refresh_from_db()

        # Redis에 카카오 토큰 저장
        redis_client.setex(RedisKeys.get_kakao_access_token_key(user.provider_id), 5 * 60 * 60, kakao_access_token)
        redis_client.setex(RedisKeys.get_kakao_refresh_token_key(user.provider_id), 5 * 60 * 60, kakao_refresh_token)

        serializer = SocialUserSerializer(user)
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        if not user.is_active:
            response = Response(
                {
                    "require_additional_info": True,  # 필수 정보를 입력받아야 한다는 의미
                    "access": access_token,
                    "user": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

            response.set_cookie(
                "refresh_token",
                value=str(refresh),
                httponly=True,
                secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
                samesite="Lax",
                max_age=5 * 60 * 60,
            )
            return response

        else:
            response = Response(
                {
                    "access": access_token,
                    "user": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

            response.set_cookie(
                "refresh_token",
                value=str(refresh),
                httponly=True,
                secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
                samesite="Lax",
                max_age=5 * 60 * 60,
            )

            return response


class SocialSignupCompleteView(APIView):
    """
    소셜로그인 추가 정보 받는 API
    """

    authentication_classes = [AllowInactiveUserJWTAuthentication]

    @extend_schema(
        summary="소셜 로그인 후 추가 정보 입력",
        description="소셜 로그인 후 부족한 정보를 입력하여 계정을 활성화합니다.",
        request=SocialSignupSerializer,
        tags=["User"],
    )
    def post(self, request):
        user = request.user
        try:
            user = User.objects.get(id=user.id)
        except User.DoesNotExist:
            return Response({"error": "존재하지 않는 계정입니다."}, status=status.HTTP_404_NOT_FOUND)

        # 소셜 로그인 유저인지 확인
        if not User.objects.filter(provider_id=user.provider_id, provider="KAKAO").exists():
            return Response({"error": "소셜 로그인 유저가 아닙니다."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({"error": "이미 활성화 된 유저입니다."})

        serializer = SocialSignupSerializer(user, data=request.data)
        if serializer.is_valid():
            try:
                with transaction.atomic():
                    user = serializer.save()
                    user.is_active = True  # 계정 활성화
                    user.save()
                    user.refresh_from_db()
                    if not Student.objects.filter(user=user).exists():
                        Student.objects.create(user=user)
                return Response({"detail": "추가 정보 입력 완료!"}, status=status.HTTP_200_OK)

            except Exception:
                return Response({"error": f"추가 정보 입력 중 오류 발생"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

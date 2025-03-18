import random
import smtplib

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.mail import send_mail
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.common.utils import redis_client
from config.settings.base import EMAIL_HOST_USER

from .models import Student, User
from .serializers import (
    ChangePasswordSerializer,
    KakaoLoginSerializer,
    LoginSerializer,
    SendEmailVerificationCodeSerializer,
    SignupSerializer,
    SocialProfileSerializer,
    UpdateMyPageSerializer,
    UserSerializer,
    VerifyEmailCodeSerializer,
)
from .utils import validate_user_password


class RedisKeys:
    """
    Redis 관련 이메일 상수 클래스
    """

    VERIFIED_EMAIL = "verified_email_{email}"
    EMAIL_VERIFICATION = "email_verification_{email}"
    EMAIL_REQUEST_LIMIT = "email_request_limit_{email}"

    @staticmethod
    def get_verified_email_key(email):
        return RedisKeys.VERIFIED_EMAIL.format(email=email)

    @staticmethod
    def get_email_verification_key(email):
        return RedisKeys.EMAIL_VERIFICATION.format(email=email)

    @staticmethod
    def get_email_request_limit_key(email):
        return RedisKeys.EMAIL_REQUEST_LIMIT.format(email=email)


class SendEmailVerificationCodeView(APIView):
    """
    이메일 인증 요청 보내는 API
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

        # Rate Limiting 적용 (30초 동안 재요청 불가) / [email_request_limit_key]가 저장되는 부분
        redis_client.setex(RedisKeys.get_email_request_limit_key(email), 30, "1")

        # 이메일 전송
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

            except Exception:
                return Response({"error": "회원가입 중 오류 발생"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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


class KakaoLoginView(APIView):

    @extend_schema(summary="카카오 로그인", description="카카오 소셜 로그인입니다", tags=["User"])
    def post(self, request):
        return


class SocialProfileCreate(APIView):

    @extend_schema(
        summary="소셜 로그인 시 프로필 생성",
        description="name, nickname, phone_number를 팝업창에서 입력할 때 사용하는 API입니다",
        request=SocialProfileSerializer,
        tags=["User"],
    )
    def post(self, request):
        return


class LogoutView(APIView):
    """
    로그아웃 API
    """

    @extend_schema(
        summary="로그아웃", description="refresh token을 blacklist에 등록 후 로그아웃하는 API입니다", tags=["User"]
    )
    def post(self, request):
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
        return response


class WithdrawalView(APIView):
    """
    회원탈퇴 API
    """

    @extend_schema(summary="회원탈퇴", description="유저를 soft delete로 관리하는 회원탈퇴 API입니다", tags=["User"])
    def post(self, request):
        # 쿠키에서 refresh token 추출
        refresh_token = request.COOKIES.get("refresh_token")
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
            except Exception:
                return Response({"에러발생, 관리자에게 문의해주세요"}, status=status.HTTP_400_BAD_REQUEST)

        # soft delete 처리 (탈퇴 상태로 저장)
        user = request.user
        user.delete()

        # refresh token 삭제 후 응답 반환
        response = Response(
            {"detail": "회원 탈퇴가 완료되었습니다. 같은 이메일로 재가입해도 데이터는 남아있지 않습니다."},
            status=status.HTTP_200_OK,
        )
        response.delete_cookie("refresh_token")
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
        if (
            user.email == request.user.email
            and user.name == request.user.name
            and user.phone_number == request.user.phone_number
        ):
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

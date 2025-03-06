import random

from django.contrib.auth import authenticate
from django.core.mail import send_mail
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from config.settings.base import EMAIL_HOST_USER
from .models import User

from .serializers import (
    ChangePasswordSerializer,
    KakaoLoginSerializer,
    LoginSerializer,
    SignupSerializer,
    SocialProfileSerializer,
    UpdateMyPageSerializer,
    UserSerializer,
    SendEmailVerificationCodeSerializer, VerifyEmailCodeSerializer,
)
import redis

from rest_framework_simplejwt.tokens import RefreshToken


redis_client = redis.StrictRedis(
    host="localhost",  # 도커에서는 redis의 컨테이너 이름으로 변경해야함
    port=6379,
    db=0,
    decode_responses=True  # 문자열 반환을 위해 decode_responses=True 설정
)

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
    @extend_schema(
        summary="이메일 인증 요청", description="유저 이메일로 인증 번호를 보냅니다", request=SendEmailVerificationCodeSerializer, tags=["User"]
    )
    def post(self, request):
        email = request.data.get("email")
        
        # 이미 인증된 이메일인지 확인
        if redis_client.get(RedisKeys.get_verified_email_key(email)):
            return Response(
                {"error": "이미 인증이 완료된 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        
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
        
        # 기존 코드가 없거나, 만료된 경우
        if existing_code or not redis_client.ttl(RedisKeys.get_email_verification_key(email)) <= 0:
            return Response(
                {"message": "인증 코드가 이미 발송되었습니다. 기존 코드를 사용하세요."},
                status=status.HTTP_200_OK,
            )

        # 인증 코드가 없거나 TTL이 만료된 경우, 기존 코드를 삭제하고 새로 생성
        redis_client.delete(RedisKeys.get_email_verification_key(email))
    
        # 6자리 랜덤 인증 코드 생성
        verification_code = str(random.randint(100000, 999999))
        
        # Redis에 인증 코드 저장 / [email_verification_key]가 저장되는 부분
        # ex=Expiration Time -> 만료시간 설정(300초)
        # nx=Not Exists -> 값이 존재하지 않으면 값을 설정
        success = redis_client.set(
            RedisKeys.get_email_verification_key(email), verification_code, ex=300, nx=True
        )
        # 만약 이미 코드가 존재했다면 기존 코드 사용
        if not success:
            verification_code = redis_client.get(RedisKeys.get_email_verification_key(email))
        
        # Rate Limiting 적용 (30초 동안 재요청 불가) / [email_request_limit_key]가 저장되는 부분
        redis_client.setex(RedisKeys.get_email_request_limit_key(email), 30, '1')
        
        # 이메일 전송
        try:
            send_mail(
                subject="소리상상 이메일 인증 코드입니다",
                message=f"당신의 이메일 인증 코드는 {verification_code} 입니다.",
                from_email=EMAIL_HOST_USER,
                recipient_list=[email],
                fail_silently=False,
            )
        except Exception as e:
            # 이메일 전송 실패 시 처리
            return Response({"detail": "이메일 전송에 실패했습니다.", "error": e}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({"message": "인증 코드가 이메일로 전송되었습니다. 5분 이내에 확인해주세요."}, status=status.HTTP_200_OK)


class VerifyEmailCodeView(APIView):
    """
    이메일 인증 확인하는 API
    """
    @extend_schema(
        summary="이메일 인증 확인", description="인증 번호가 맞는지 확인합니다", request=VerifyEmailCodeSerializer, tags=["User"]
    )
    def post(self, request):
        email = request.data.get("email")
        input_code = request.data.get("code")

        # 저장된 인증 코드 가져오기
        stored_code = redis_client.get(RedisKeys.get_email_verification_key(email))

        if stored_code is None:
            return Response(
                {"error": "인증코드를 다시 발급받으세요."}, status=status.HTTP_400_BAD_REQUEST
            )
        
        # Redis에서 가져온 데이터가 bytes일 경우 decode 처리
        if isinstance(stored_code, bytes):
            stored_code = stored_code.decode()
        
        if stored_code != input_code:
            return Response({"error": "잘못된 인증 코드입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 이메일 인증 완료 여부 저장 / [verified_email_key]가 저장되는 부분
        redis_client.setex(RedisKeys.get_verified_email_key(email), 3600, "true")
        
        redis_client.delete(RedisKeys.get_email_verification_key(email))

        return Response({"message": "이메일 인증이 완료되었습니다!"}, status=status.HTTP_200_OK)


class SignUpView(APIView):
    """
    회원가입 API
    """
    @extend_schema(
        summary="회원가입", description="회원정보를 입력받아 새 사용자를 생성", request=SignupSerializer, tags=["User"]
    )
    def post(self, request):
        email = request.data.get("email")
        # 이메일 인증 여부 확인
        is_verified = redis_client.get(RedisKeys.get_verified_email_key(email))
        
        if is_verified is None:
            return Response(
                {"error": "이메일 인증이 완료되지 않았습니다."}, status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = SignupSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()  # 사용자 생성
            
            # 회원가입 완료 후 인증 데이터 삭제 (불필요한 Redis의 데이터를 정리)
            redis_client.delete(RedisKeys.get_verified_email_key(email))
            
            return Response({"message": "회원가입 성공!"}, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):

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
        
        user = authenticate(email=email, password=password) # db에 유저가 있는지 검증
        
        if not User.objects.filter(email=email).exists():
            return Response({"detail": "존재하지 않는 이메일입니다."}, status=status.HTTP_400_BAD_REQUEST)
        
        if user is not None:  # 유저인증에 성공하면 True
            refresh = RefreshToken.for_user(user)  # JWT token 생성
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            user_data = User.objects.get(email=email)
            serializer = UserSerializer(user_data)
            
            # access token 은 JSON 응답으로 반환
            response = Response({"access_token": access_token, "user": serializer.data}, status=status.HTTP_200_OK)
            return response
        else:
            return Response({"detail": "잘못된 비밀번호입니다."}, status=status.HTTP_401_UNAUTHORIZED)


class KakaoLoginView(APIView):

    @extend_schema(summary="카카오 로그인", description="카카오 소셜 로그인입니다", tags=["User"])
    def post(self, request):
        return


class Social_profile_create(APIView):

    @extend_schema(
        summary="소셜 로그인 시 프로필 생성",
        description="name, nickname, phone_number를 팝업창에서 입력할 때 사용하는 API입니다",
        request=SocialProfileSerializer,
        tags=["User"],
    )
    def post(self, request):
        return


class LogoutView(APIView):

    @extend_schema(
        summary="로그아웃", description="refresh token을 blacklist에 등록 후 로그아웃하는 API입니다", tags=["User"]
    )
    def post(self, request):
        return


class WithdrawalView(APIView):

    @extend_schema(summary="회원탈퇴", description="유저를 soft delete로 관리하는 회원탈퇴 API입니다", tags=["User"])
    def post(self, request):
        return


class MyinfoView(APIView):

    @extend_schema(
        summary="회원 정보 조회",
        description="회원 정보를 조회하는 API입니다",
        responses={200, UserSerializer},
        tags=["User"],
    )
    def get(self, request):
        return

    @extend_schema(
        summary="회원 정보 수정",
        description="회원 정보를 수정하는 API입니다",
        request=UpdateMyPageSerializer,
        tags=["User"],
    )
    def patch(self, request):
        return


class ChangePasswordView(APIView):

    @extend_schema(
        summary="비밀번호 변경",
        description="비밀번호를 변경하는 API입니다",
        request=ChangePasswordSerializer,
        tags=["User"],
    )
    def patch(self, request):
        return

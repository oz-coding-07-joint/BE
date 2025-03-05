from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    ChangePasswordSerializer,
    KakaoLoginSerializer,
    LoginSerializer,
    SignupSerializer,
    SocialProfileSerializer,
    UpdateMyPageSerializer,
    UserSerializer,
)


class SignUpView(APIView):

    @extend_schema(
        summary="회원가입", description="회원정보를 입력받아 새 사용자를 생성", request=SignupSerializer, tags=["User"]
    )
    def post(self, request):
        return


class LoginView(APIView):

    @extend_schema(
        summary="로그인", description="이메일과 비밀번호를 받아 로그인합니다", request=LoginSerializer, tags=["User"]
    )
    def post(self, request):
        return


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

import uuid

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.db import transaction

from .models import User


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """소셜 로그인 회원 탈퇴 유저의 경우 삭제 후 로그인 진행"""
        email = sociallogin.account.extra_data.get("email")

        with transaction.atomic():
            deleted_user = User.deleted_objects.filter(email=email).first()
            if deleted_user:
                deleted_user.hard_delete()

    def populate_user(self, request, sociallogin, data):
        """소셜 로그인 후 유저 정보 채우기"""
        user = super().populate_user(request, sociallogin, data)

        # 중복되지 않는 임시 닉네임과 번호 부여
        user.nickname = uuid.uuid4().hex[:20]  # 임의의 닉네임
        user.phone_number = uuid.uuid4().hex[:20]  # 가짜 번호
        user.is_active = False  # 활성화되지 않은 상태로 저장
        user.provider = "KAKAO"

        return user

    def save_user(self, request, sociallogin, form=None):
        super().save_user(request, sociallogin, form)

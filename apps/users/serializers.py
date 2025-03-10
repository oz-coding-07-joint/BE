import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework import serializers

from apps.common.utils import redis_client

from ..terms.models import Terms, TermsAgreement
from ..terms.serializers import TermsAgreementSerializer
from .models import User
from .utils import get_kakao_user_data


class SendEmailVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            "id",
            "name",
            "nickname",
            "email",
            "phone_number",
            "provider",
            "is_active",
            "is_staff",
            "is_superuser",
        )


class SignupSerializer(serializers.ModelSerializer):
    terms_agreements = TermsAgreementSerializer(many=True, write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "name", "nickname", "phone_number", "terms_agreements")
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, email):
        # 이메일이 인증되었는지 2차 확인
        if not redis_client.get(f"verified_email_{email}"):
            raise serializers.ValidationError("이메일 인증을 먼저 완료해야 합니다.")
        return email

    def validate_password(self, password):
        if not re.search(r"[a-zA-Z]", password) or not re.search(r"[!@#$%^&*()]", password):
            raise serializers.ValidationError(
                "비밀번호는 8자 이상의 영문, 숫자, 특수문자[!@#$%^&*()]를 포함해야 합니다."
            )

        try:
            validate_password(password)  # 장고의 비밀번호 유효성 검사
        except ValidationError as e:
            raise serializers.ValidationError(", ".join(e.messages))

        return password

    def validate_phone_number(self, phone_number):
        """휴대폰 번호가 숫자인지 확인"""
        if not phone_number.isdigit():
            raise serializers.ValidationError("휴대폰 번호는 숫자만 입력해야 합니다.")

        if User.objects.filter(phone_number=phone_number).exists():
            raise serializers.ValidationError("이미 등록된 휴대폰 번호입니다.")

        return phone_number

    def validate_terms_agreements(self, value):
        # value 예시
        # value = [
        #     {"terms": 1, "is_active": True},
        #     {"terms": 2, "is_active": False},
        #     {"terms": 3, "is_active": True}
        # ]

        # flat=True를 사용해서 id를 리스트로 반환 / ex -> <QuerySet [1, 2]> (1개의 필드에만 사용 가능)
        # 사용하지 않으면 튜플 / ex -> <QuerySet [(1,), (2,)]>
        # 집합 변환 시 예를 들어보면 {1, 2, 3}, {(1,), (2,), (3,)}의 차이를 보임
        # -> 튜플로 집합을 만들면 뒤에서 사용할 if문에서 사칙연산에 어려움이 생김
        required_terms = set(Terms.objects.filter(is_required=True, is_active=True).values_list("id", flat=True))

        # is_active가 true일 경우 value를 item에 1개씩 담아준다
        # item["terms"]가 Terms모델의 인스턴스이면 id를 가져오고 이미 id라면 그대로 사용
        agreed_terms = {
            item["terms"].id if isinstance(item["terms"], Terms) else item["terms"]
            for item in value
            if bool(item.get("is_agree"))
        }

        # 필수 약관에서 동의한 약관을 빼면 동의하지 않은 필수 약관이 남는다
        if required_terms - agreed_terms:
            raise serializers.ValidationError("회원가입을 위해서는 모든 필수 약관에 동의해야 합니다.")

        return value

    def create(self, validated_data):
        """
        비밀번호 해쉬화 및 terms_agreements를 생성하는 함수
        """
        terms_data = validated_data.pop("terms_agreements")
        password = validated_data.pop("password", None)

        # 약관동의 없이 회원가입 될 가능성이 있으니 트랜젝션 처리
        with transaction.atomic():
            user = User(**validated_data)

            if password:  # 비밀번호 해쉬화
                user.set_password(password)
            user.save()

            terms_agreements = [TermsAgreement(user=user, **terms) for terms in terms_data]

            # bulk_create는 여러 개의 데이터를 한 번에 insert해준다
            TermsAgreement.objects.bulk_create(terms_agreements)

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class KakaoLoginSerializer(serializers.Serializer):
    access_token = serializers.CharField()  # 카카오에서 받은 액세스 토큰

    def validate_access_token(self, value):
        """카카오 액세스 토큰 검증 및 사용자 데이터 가져오기"""
        user_data = get_kakao_user_data(value)  # 카카오 API를 통해 사용자 정보 가져오기
        if not user_data:
            raise serializers.ValidationError("유효하지 않은 액세스 토큰입니다.")
        self.context["user_data"] = user_data  # 사용자 데이터 저장
        return value

    def create(self, validated_data):
        """카카오 로그인 후 사용자 생성 및 약관 동의 처리"""
        user_data = self.context["user_data"]
        email = user_data.get("email")

        # 이메일이 이미 존재하는 경우 업데이트 또는 새 사용자 생성
        user, created = User.objects.get_or_create(email=email)

        # 기존 사용자가 아니면, 약관 동의를 처리해야 함
        if created:
            # 카카오 로그인 사용자는 반드시 약관에 동의해야 함
            terms_agreements_data = validated_data.get("terms_agreements", [])
            terms_agreements = TermsAgreementSerializer(data=terms_agreements_data, many=True)
            terms_agreements.is_valid(raise_exception=True)
            terms_agreements.save(user=user)

        return user


class SocialProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("name", "nickname", "phone_number")


class UpdateMyPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("name", "email", "phone_number")


class ChangePasswordSerializer(serializers.Serializer[User]):
    old_password = serializers.CharField(help_text="현재 비밀번호", write_only=True)
    new_password = serializers.CharField(help_text="새 비밀번호", write_only=True)

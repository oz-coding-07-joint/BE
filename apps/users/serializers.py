from rest_framework import serializers

from ..terms.models import Terms, TermsAgreement
from ..terms.serializers import TermsAgreementSerializer
from .models import User
from .utils import get_kakao_user_data


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

    def validate_terms_agreements(self, value):
        """필수 약관 동의 여부 검증"""
        # filter(): 조건에 맞는 쿼리셋을 반환
        # .all() 을 붙여도 동일한 결과를 내지만 중복된 호출이므로 filter(is_active=True) 만 사용
        # 데이터를 집합 자료형으로 변환 / 중복을 제거하고 수학적 집합 연산을 효율적으로 수행할 수 있어서 존재 여부를 빠르게 확인 가능
        required_terms = set(Terms.objects.filter(is_required=True, is_active=True).values_list("id", flat=True))
        agreed_terms = set()

        for item in value:
            if item.get("is_active"):
                term_obj = item.get("terms")
                # 만약 term_obj 가 Terms 인스턴스라면 id 를 추출, 아니면 그대로 사용
                agreed_terms.add(term_obj.id if hasattr(term_obj, "id") else term_obj)

        if required_terms - agreed_terms:
            raise serializers.ValidationError("회원가입을 위해서는 모든 필수 약관에 동의해야 합니다.")

        return value

    def create(self, validated_data):
        """User 생성 및 약관 동의 정보 저장"""
        terms_data = validated_data.pop("terms_agreements", [])  # 기본값 [] (KeyError 방지)
        password = validated_data.pop("password", None)

        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()

        for term in terms_data:
            TermsAgreement.objects.create(user=user, **term)

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

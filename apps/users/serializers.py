from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.utils import IntegrityError
from rest_framework import serializers

from ..terms.models import TermsAgreement
from ..terms.serializers import TermsAgreementSerializer
from .exceptions import UserValidationError
from .models import User
from .utils import (
    validate_signup_terms_agreements,
    validate_user_email,
    validate_user_password,
    validate_user_phone_number,
)


class SendEmailVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerifyEmailCodeSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField()


class UserSerializer(serializers.ModelSerializer):
    student_id = serializers.SerializerMethodField()
    instructor_id = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "provider",
            "email",
            "name",
            "nickname",
            "phone_number",
            "is_active",
            "is_staff",
            "is_superuser",
            "student_id",
            "instructor_id",
        )

    def get_student_id(self, obj):
        """User가 Student와 연결되어 있다면 student_id 반환, 없으면 None"""
        return obj.student.id if hasattr(obj, "student") else None

    def get_instructor_id(self, obj):
        """User가 Instructor와 연결되어 있다면 instructor_id 반환, 없으면 None"""
        return obj.instructor.id if hasattr(obj, "instructor") else None


class SocialUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "provider", "name", "nickname", "phone_number", "is_active", "is_staff", "is_superuser")


class SignupSerializer(serializers.ModelSerializer):
    terms_agreements = TermsAgreementSerializer(many=True, write_only=True)

    class Meta:
        model = User
        fields = ("email", "password", "name", "nickname", "phone_number", "terms_agreements")
        extra_kwargs = {"password": {"write_only": True}}

    def validate_email(self, email):
        return validate_user_email(email)

    def validate_password(self, password):
        return validate_user_password(password)

    def validate_phone_number(self, phone_number):
        return validate_user_phone_number(phone_number)

    def validate_terms_agreements(self, value):
        return validate_signup_terms_agreements(value)

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

            # 약관 동의 중복을 방지하기 위한 조건
            existing_terms = TermsAgreement.objects.filter(user=user)
            new_terms = [
                TermsAgreement(user=user, **terms)
                for terms in terms_data
                if not existing_terms.filter(**terms).exists()  # 이미 동의한 약관은 제외
            ]

            # 새 약관이 있다면 저장
            if new_terms:
                TermsAgreement.objects.bulk_create(new_terms)

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


class SocialSignupSerializer(serializers.ModelSerializer):
    terms_agreements = TermsAgreementSerializer(many=True, write_only=True)

    class Meta:
        model = User
        fields = ("id", "name", "nickname", "phone_number", "terms_agreements")

    def validate_phone_number(self, phone_number):
        return validate_user_phone_number(phone_number)

    def validate_terms_agreements(self, value):
        return validate_signup_terms_agreements(value)

    def update(self, instance, validated_data):
        """기존 유저 정보 업데이트 및 약관 동의 저장"""

        name = validated_data.pop("name")
        nickname = validated_data.pop("nickname")
        phone_number = validated_data.pop("phone_number")
        terms_data = validated_data.pop("terms_agreements")

        with transaction.atomic():
            instance.name = name
            instance.nickname = nickname
            instance.phone_number = phone_number
            instance.save()

            existing_terms = TermsAgreement.objects.filter(user=instance)
            new_terms = [
                TermsAgreement(user=instance, **terms)
                for terms in terms_data
                if not existing_terms.filter(**terms).exists()
            ]
            try:
                if new_terms:
                    TermsAgreement.objects.bulk_create(new_terms)

            except IntegrityError:
                raise UserValidationError("이미 약관 동의를 하셨습니다.")

            return instance


class UpdateMyPageSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=False)
    name = serializers.CharField(required=False)
    phone_number = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = ("email", "name", "phone_number")

    def validate_email(self, email):
        if self.instance.email == email:
            return email
        return validate_user_email(email)

    def validate_phone_number(self, phone_number):
        if self.instance.phone_number == phone_number:
            return phone_number
        return validate_user_phone_number(phone_number)

    def update(self, instance, validated_data):
        email = validated_data.get("email", instance.email)
        name = validated_data.get("name", instance.name)
        phone_number = validated_data.get("phone_number", instance.phone_number)

        instance.email = email
        instance.name = name
        instance.phone_number = phone_number

        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer[User]):
    old_password = serializers.CharField(help_text="현재 비밀번호", write_only=True)
    new_password = serializers.CharField(help_text="새 비밀번호", write_only=True)

    def validate_old_password(self, value):
        user = self.context["request"].user  # 요청에서 사용자 정보 가져오기
        if not user.check_password(value):
            raise UserValidationError("현재 비밀번호가 일치하지 않습니다.")
        return value

    def validate_new_password(self, value):
        old_password = self.initial_data.get("old_password")
        if old_password == value:
            raise UserValidationError("이전 비밀번호와 같게 설정할 수 없습니다.")

        try:
            validate_user_password(value)

        except ValidationError as e:
            raise UserValidationError(str(e))

        return value

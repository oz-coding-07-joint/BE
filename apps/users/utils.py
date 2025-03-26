import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.common.utils import redis_client
from apps.terms.models import Terms
from apps.users.models import User


def validate_signup_terms_agreements(value):
    """
    value 예시
    value = [
        {"terms": 1, "is_active": True},
        {"terms": 2, "is_active": False},
        {"terms": 3, "is_active": True}
    ]

    flat=True를 사용해서 id를 리스트로 반환 / ex -> <QuerySet [1, 2]> (1개의 필드에만 사용 가능)
    사용하지 않으면 튜플 / ex -> <QuerySet [(1,), (2,)]>
    집합 변환 시 예를 들어보면 {1, 2, 3}, {(1,), (2,), (3,)}의 차이를 보임
    -> 튜플로 집합을 만들면 뒤에서 사용할 if문에서 사칙연산에 어려움이 생김
    """
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


def validate_user_email(email):
    # 이메일이 인증되었는지 2차 확인
    if not redis_client.get(f"verified_email_{email}"):
        raise serializers.ValidationError("이메일 인증을 먼저 완료해야 합니다.")
    return email


def validate_user_password(password):
    if not re.search(r"[a-zA-Z]", password) or not re.search(r"[!@#$%^&*()]", password):
        raise serializers.ValidationError("비밀번호는 8자 이상의 영문, 숫자, 특수문자[!@#$%^&*()]를 포함해야 합니다.")

    try:
        validate_password(password)  # 장고의 비밀번호 유효성 검사
    except ValidationError as e:
        raise serializers.ValidationError(", ".join(e.messages))

    return password


def validate_user_phone_number(phone_number):
    """휴대폰 번호가 숫자인지 확인"""
    if not phone_number.isdigit():
        raise serializers.ValidationError("휴대폰 번호는 숫자만 입력해야 합니다.")

    if User.objects.filter(phone_number=phone_number).exists() or User.deleted_objects.filter(phone_number=phone_number).exists():
        raise serializers.ValidationError("이미 등록된 휴대폰 번호입니다.")

    return phone_number

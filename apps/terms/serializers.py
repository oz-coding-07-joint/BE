from rest_framework import serializers

from .models import Terms, TermsAgreement


class TermsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Terms
        fields = ("id", "name", "detail", "is_active", "is_required")


class TermsAgreementSerializer(serializers.ModelSerializer):
    terms_detail = TermsSerializer(source="terms", read_only=True)

    class Meta:
        model = TermsAgreement
        fields = ("id", "terms", "terms_detail", "is_agree")
        # fields에 terms가 있지만 write_only=True이므로 response에서 terms가 보이지 않음
        extra_kwargs = {
            "terms": {"write_only": True},
        }

from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User


# 약관 정보를 저장하는 모델
class Terms(BaseModel):
    name = models.CharField(max_length=50)
    detail = models.TextField()
    is_active = models.BooleanField(default=True)
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = "terms"
        verbose_name = "Terms"
        verbose_name_plural = "Terms"

    def __str__(self):
        return f"{self.name}"


# 사용자의 약관 동의 정보를 저장하는 모델
class TermsAgreement(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    terms = models.ForeignKey("Terms", on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "terms_agreement"

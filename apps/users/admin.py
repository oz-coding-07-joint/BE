from django.contrib import admin
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError

from apps.common.admin import BaseModelAdmin

from .models import User


# Register your models here.
@admin.register(User)
class UserAdmin(BaseModelAdmin):
    # 표시할 컬럼
    list_display = ("email", "nickname", "is_staff", "is_active", "is_superuser")
    # 검색 기능 설정
    search_fields = ("email", "nickname")
    # 필터링 조건
    list_filter = ("is_active", "is_staff", "is_superuser")

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        if not request.user.is_superuser:
            form.base_fields["is_superuser"].disabled = True
            form.base_fields["is_staff"].disabled = True
        return form

    def save_model(self, request, obj, form, change):
        """
        최후의 superuser가 해제되지 않도록 방지
        유저 생성 시 비밀번호 해쉬화
        """
        if change and "is_superuser" in form.changed_data:
            if not obj.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
                raise ValidationError("최소 1명의 superuser는 있어야 합니다.")

        if obj.password:
            obj.password = make_password(obj.password)

        super().save_model(request, obj, form, change)

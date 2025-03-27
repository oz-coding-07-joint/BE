from django.contrib import admin, messages
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ValidationError
from django_softdelete.admin import GlobalObjectsModelAdmin
from django_softdelete.models import SoftDeleteModel

from apps.common.admin import BaseModelAdmin

from .models import Instructor, Student, User


# Register your models here.
@admin.register(User)
class UserAdmin(BaseModelAdmin, GlobalObjectsModelAdmin):
    # 표시할 컬럼
    list_display = ("email", "nickname", "provider", "is_staff", "is_active", "is_superuser", "deleted_at")
    # 검색 기능 설정
    search_fields = ("email", "nickname")
    # 필터링 조건
    list_filter = ("provider", "is_active", "is_staff", "is_superuser", "deleted_at")
    actions = ["delete_instructor"]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        form.base_fields["provider"].disabled = True
        form.base_fields["provider_id"].required = False  # 필수 입력 해제
        form.base_fields["provider_id"].disabled = True  # 비활성화

        # 슈퍼유저가 아닐 경우 아래 두 필드를 비활성화
        if not request.user.is_superuser:
            form.base_fields["is_superuser"].disabled = True
            form.base_fields["is_staff"].disabled = True
        return form

    def get_readonly_fields(self, request, obj=None):
        """
        마지막 superuser가 존재하면 해당 필드를 읽기 전용으로 설정
        """
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj and obj.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
            readonly_fields = readonly_fields + ("is_superuser",)

        return readonly_fields

    def save_model(self, request, obj, form, change):
        """
        1) 최후의 superuser가 해제되지 않도록 2차 방지
        2) 유저 생성 시 비밀번호 해쉬화
        """
        if change and "is_superuser" in form.changed_data:
            if not obj.is_superuser and User.objects.filter(is_superuser=True).count() == 1:
                raise ValidationError("최소 1명의 superuser는 있어야 합니다.")

        if "password" in form.changed_data:
            obj.password = make_password(obj.password)

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser  # superuser만 삭제 가능

    def delete_model(self, request, obj):
        """단일 객체 삭제 시 하드 딜리트 적용"""
        if isinstance(obj, SoftDeleteModel):
            obj.hard_delete()
        messages.success(request, "영구 삭제되었습니다.")

    def delete_queryset(self, request, queryset):
        """다중 객체 삭제 시 하드 딜리트 적용"""
        count = queryset.count()
        for obj in queryset:
            if isinstance(obj, SoftDeleteModel):
                obj.hard_delete()
        messages.success(request, f"{count}개 항목이 영구 삭제되었습니다.")


@admin.register(Student)
class StudentAdmin(BaseModelAdmin, GlobalObjectsModelAdmin):
    list_display = ("get_user_email", "get_user_name", "created_at", "updated_at", "deleted_at")
    search_fields = ("user__email", "user__name")
    list_filter = ("created_at", "updated_at", "deleted_at")

    def get_user_email(self, obj):
        return obj.user.email

    def get_user_name(self, obj):
        return obj.user.name

    get_user_email.short_description = "Email"
    get_user_name.short_description = "Name"


@admin.register(Instructor)
class InstructorAdmin(BaseModelAdmin, GlobalObjectsModelAdmin):
    list_display = ("get_user_email", "get_user_name", "experience", "created_at", "updated_at", "deleted_at")
    search_fields = ("user__email", "user__name", "experience")
    list_filter = ("created_at", "updated_at", "deleted_at")

    def get_user_email(self, obj):
        return obj.user.email

    def get_user_name(self, obj):
        return obj.user.name

    get_user_email.short_description = "Email"
    get_user_name.short_description = "Name"

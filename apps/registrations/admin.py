from django.contrib import admin

from apps.common.admin import BaseModelAdmin

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(BaseModelAdmin):
    """Enrollment 모델 관리자.

    Enrollment 인스턴스의 리스트 뷰에서 표시할 필드와 검색 기능을 정의.
    """

    list_display = ("course_title", "student", "is_active", "created_at", "updated_at")
    search_fields = ("course__title", "student__user__email", "student__user__username")

    def course_title(self, obj):
        """연결된 강의의 제목을 반환.

        Args:
            obj (Enrollment): Enrollment 인스턴스.

        Returns:
            str: 연결된 강의의 제목.
        """
        return obj.course.title

    course_title.short_description = "Course"

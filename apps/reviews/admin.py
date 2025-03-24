from django.contrib import admin

from apps.common.admin import BaseModelAdmin
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(BaseModelAdmin):
    """Review 모델 관리자.

    Review 인스턴스의 리스트 뷰에서 표시할 필드와 검색 기능을 정의.
    """
    list_display = ("lecture_title", "student", "student_nickname", "star", "content", "created_at", "updated_at")
    search_fields = ("lecture__title", "student__user__email", "student__user__username", "student_nickname", "content")

    def lecture_title(self, obj):
        """연결된 강의의 제목을 반환.

        Args:
            obj (Review): Review 인스턴스.

        Returns:
            str: 연결된 강의의 제목.
        """
        return obj.lecture.title

    lecture_title.short_description = "Lecture"

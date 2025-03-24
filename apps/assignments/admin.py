from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Assignment, AssignmentComment


@admin.register(Assignment)
class AssignmentAdmin(BaseModelAdmin):
    """Assignment 모델 관리자.

    Assignment 인스턴스의 리스트 뷰에서 표시할 필드와 검색 기능을 정의.
    """

    list_display = ("title", "file_url", "chapter_video", "created_at", "updated_at")
    search_fields = ("title", "content")


@admin.register(AssignmentComment)
class AssignmentCommentAdmin(BaseModelAdmin):
    """AssignmentComment 모델 관리자.

    AssignmentComment 인스턴스의 리스트 뷰에서 표시할 필드와 검색 기능을 정의.
    """

    list_display = (
        "assignment_title",
        "user_nickname",
        "user",
        "content",
        "parent",
        "assignment",
        "created_at",
    )
    search_fields = ("content", "user__nickname", "assignment__title")

    def assignment_title(self, obj):
        """과제 제목을 반환.

        Args:
            obj (AssignmentComment): 댓글 인스턴스.

        Returns:
            str: 연결된 과제의 제목.
        """
        return obj.assignment.title

    assignment_title.short_description = "과제 제목"

    def user_nickname(self, obj):
        """댓글 작성자의 닉네임을 반환.

        Args:
            obj (AssignmentComment): 댓글 인스턴스.

        Returns:
            str: 댓글 작성자의 닉네임 (없으면 빈 문자열).
        """
        return getattr(obj.user, "nickname", "")

    user_nickname.short_description = "닉네임"

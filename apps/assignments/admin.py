from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Assignment, AssignmentComment


@admin.register(Assignment)
class AssignmentAdmin(BaseModelAdmin):
    list_display = ("title", "file_url", "chapter_video", "created_at", "updated_at")
    search_fields = ("title", "content")


@admin.register(AssignmentComment)
class AssignmentCommentAdmin(BaseModelAdmin):
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
        return obj.assignment.title

    assignment_title.short_description = "과제 제목"

    def user_nickname(self, obj):
        return getattr(obj.user, "nickname", "")

    user_nickname.short_description = "닉네임"

from django import forms
from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Assignment, AssignmentComment


@admin.register(Assignment)
class AssignmentAdmin(BaseModelAdmin):
    """Assignment 모델 관리자.

    Assignment 인스턴스의 리스트 뷰에서 표시할 필드와 검색 기능을 정의.
    """

    list_display = ("title", "file_url", "chapter_video", "get_lecture_chapter_id", "created_at", "updated_at")
    search_fields = ("title", "content")
    readonly_fields = ("get_lecture_chapter_id",)

    def get_lecture_chapter_id(self, obj):
        """연결된 ChapterVideo의 lecture_chapter ID를 반환.

        Args:
            obj (Assignment): Assignment 인스턴스.

        Returns:
            int or None: 연결된 lecture_chapter의 ID, 존재하지 않으면 None.
        """
        return (
            obj.chapter_video.lecture_chapter.id
            if obj.chapter_video and hasattr(obj.chapter_video, "lecture_chapter")
            else None
        )

    get_lecture_chapter_id.short_description = "Lecture Chapter ID"


class ParentAssignmentCommentChoiceField(forms.ModelChoiceField):
    """부모 AssignmentComment 선택 필드.

    드롭다운 항목에 유저 닉네임, 과제 제목, 생성일(년-월-일 시:분:초) 형식으로 레이블을 표시.
    """

    def label_from_instance(self, obj):
        """AssignmentComment 인스턴스로부터 라벨을 생성.

        Args:
            obj (AssignmentComment): AssignmentComment 인스턴스.

        Returns:
            str: '유저 닉네임, 과제 제목, 생성일(년-월-일 시:분:초)' 형식의 문자열.
        """
        formatted_date = obj.created_at.strftime("%Y-%m-%d %H:%M:%S")
        return f"{obj.user.nickname}, {obj.assignment.title}, {formatted_date}"


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

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """외래키 필드에 대해 커스텀 ModelChoiceField를 사용.

        부모 필드(parent)에 대해 ParentAssignmentCommentChoiceField를 적용하여
        드롭다운 항목에 유저 닉네임, 과제 제목이 표시되도록 재정의.

        Args:
            db_field: 현재 처리 중인 데이터베이스 필드.
            request (Request): 요청 객체.
            **kwargs: 추가 인자.

        Returns:
            Field: 재정의된 폼 필드.
        """
        if db_field.name == "parent":
            kwargs["queryset"] = AssignmentComment.objects.all()
            kwargs["form_class"] = ParentAssignmentCommentChoiceField
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import ChapterVideo, Course, Lecture, LectureChapter, ProgressTracking


@admin.register(Course)
class CourseAdmin(BaseModelAdmin):
    list_display = ("title", "price", "total_duration", "max_students")
    search_fields = ("title",)
    list_filter = ("total_duration", "max_students")


@admin.register(Lecture)
class LectureAdmin(BaseModelAdmin):
    list_display = ("title", "course", "instructor", "thumbnail")


@admin.register(LectureChapter)
class LectureChapterAdmin(BaseModelAdmin):
    list_display = ("title", "lecture", "material_url")


@admin.register(ChapterVideo)
class ChapterVideoAdmin(BaseModelAdmin):
    list_display = ("title", "lecture_chapter", "video_url")


@admin.register(ProgressTracking)
class ProgressTrackingAdmin(admin.ModelAdmin):
    list_display = ("id", "student", "chapter_video_title", "progress", "is_completed", "last_watched_time")
    search_fields = ("student__user__username", "chapter_video__title")
    list_filter = ("is_completed",)
    ordering = ("-id",)

    def chapter_video_title(self, obj):
        """강의 영상 제목 반환"""
        return obj.chapter_video.title if obj.chapter_video else "N/A"

    chapter_video_title.short_description = "강의 영상 제목"

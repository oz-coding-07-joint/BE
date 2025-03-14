from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import ChapterVideo, Course, Lecture, LectureChapter


@admin.register(Course)
class CourseAdmin(BaseModelAdmin):
    pass


@admin.register(Lecture)
class LectureAdmin(BaseModelAdmin):
    list_display = ("title", "course", "instructor", "thumbnail")


@admin.register(LectureChapter)
class LectureChapterAdmin(BaseModelAdmin):
    list_display = ("title", "lecture", "material_url")


@admin.register(ChapterVideo)
class ChapterVideoAdmin(BaseModelAdmin):
    list_display = ("title", "lecture_chapter", "video_url")

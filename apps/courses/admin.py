from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import ChapterVideo, Course, Lecture, LectureChapter


@admin.register(Course)
class CourseAdmin(BaseModelAdmin):
    pass


@admin.register(Lecture)
class LectureAdmin(BaseModelAdmin):
    pass


@admin.register(LectureChapter)
class LectureChapterAdmin(BaseModelAdmin):
    pass


@admin.register(ChapterVideo)
class ChapterVideoAdmin(BaseModelAdmin):
    pass

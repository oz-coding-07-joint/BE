from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Course, CourseMaterial, Lecture, LectureCourse


@admin.register(Course)
class CourseAdmin(BaseModelAdmin):
    pass


@admin.register(Lecture)
class LectureAdmin(BaseModelAdmin):
    pass


@admin.register(LectureCourse)
class LectureCourseAdmin(BaseModelAdmin):
    pass


@admin.register(CourseMaterial)
class CourseMaterialAdmin(BaseModelAdmin):
    pass

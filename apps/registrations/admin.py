from django.contrib import admin

from apps.common.admin import BaseModelAdmin

from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(BaseModelAdmin):
    list_display = ("course_title", "student", "is_active", "created_at", "updated_at")
    search_fields = ("course__title", "student__user__email", "student__user__username")

    def course_title(self, obj):
        return obj.course.title

    course_title.short_description = "Course"

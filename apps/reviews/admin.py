from django.contrib import admin

from apps.common.admin import BaseModelAdmin
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(BaseModelAdmin):
    list_display = ("lecture_title", "student", "student_nickname", "star", "content", "created_at", "updated_at")
    search_fields = ("lecture__title", "student__user__email", "student__user__username", "student_nickname", "content")

    def lecture_title(self, obj):
        return obj.lecture.title

    lecture_title.short_description = "Lecture"

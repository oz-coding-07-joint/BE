from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Assignment, AssignmentComment


@admin.register(Assignment)
class AssignmentAdmin(BaseModelAdmin):
    pass


@admin.register(AssignmentComment)
class AssignmentCommentAdmin(BaseModelAdmin):
    pass

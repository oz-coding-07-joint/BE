from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Homework, HomeworkFeedback, Task


@admin.register(Task)
class TaskAdmin(BaseModelAdmin):
    pass


@admin.register(Homework)
class HomeworkAdmin(BaseModelAdmin):
    pass


@admin.register(HomeworkFeedback)
class HomeworkFeedbackAdmin(BaseModelAdmin):
    pass

from django.contrib import admin

from apps.common.admin import BaseModelAdmin
from .models import Enrollment


@admin.register(Enrollment)
class EnrollmentAdmin(BaseModelAdmin):
    pass
from django.contrib import admin

from apps.common.admin import BaseModelAdmin
from apps.reviews.models import Review


@admin.register(Review)
class ReviewAdmin(BaseModelAdmin):
    pass

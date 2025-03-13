from django.contrib import admin

from ..common.admin import BaseModelAdmin
from .models import Terms, TermsAgreement


# Register your models here.
@admin.register(Terms)
class TermsAdmin(BaseModelAdmin):
    pass


@admin.register(TermsAgreement)
class TermsAgreementAdmin(BaseModelAdmin):
    list_display = ("user__email", "terms", "is_agree")
    search_fields = ("user__email",)
    list_filter = ("terms", "is_agree")
from django.contrib import admin
from .models import Terms, TermsAgreement
from ..common.admin import BaseModelAdmin


# Register your models here.
@admin.register(Terms)
class TermsAdmin(BaseModelAdmin):
    pass


@admin.register(TermsAgreement)
class TermsAgreementAdmin(BaseModelAdmin):
    pass
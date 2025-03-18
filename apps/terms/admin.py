from django.contrib import admin, messages
from django_softdelete.admin import GlobalObjectsModelAdmin
from django_softdelete.models import SoftDeleteModel

from ..common.admin import BaseModelAdmin
from .models import Terms, TermsAgreement


# Register your models here.
@admin.register(Terms)
class TermsAdmin(BaseModelAdmin):
    pass


@admin.register(TermsAgreement)
class TermsAgreementAdmin(BaseModelAdmin, GlobalObjectsModelAdmin):
    list_display = ("user__email", "terms", "is_agree", "deleted_at")
    search_fields = ("user__email",)
    list_filter = ("terms", "is_agree", "deleted_at")
    actions = ["delete_instructor"]

    def delete_model(self, request, obj):
        count = 0
        if isinstance(obj, SoftDeleteModel):
            obj.hard_delete()
            count += 1
        messages.success(request, f"{count}개 항목이 영구 삭제되었습니다.")

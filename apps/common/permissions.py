from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.registrations.models import Enrollment


class IsActiveStudent(BasePermission):
    """
    로그인한 사용자 중 수강신청이 승인된 학생만 접근 가능.
    미승인된 사용자는 프론트의 강의 소개 페이지로 리다이렉트.
    """

    def has_permission(self, request, view):
        # 1️⃣ 사용자 인증 확인
        if not request.user or not request.user.is_authenticated:
            return False

        # 2️⃣ 수강 신청이 승인된 학생인지 확인
        if not Enrollment.objects.filter(user=request.user, is_active=True).exists():
            frontend_url = getattr(settings, "FRONTEND_URL", "https://example.com")
            redirect_url = frontend_url.rstrip("/") + "/lectures/introduction/"
            return Response({"redirect_url": redirect_url}, status=302)

        return True

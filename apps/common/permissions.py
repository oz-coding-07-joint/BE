from rest_framework.permissions import BasePermission
from apps.registrations.models import Enrollment

class IsActiveStudent(BasePermission):
    """
    로그인한 사용자 중 수강신청이 승인된 학생만 접근 가능.
    """

    def has_permission(self, request, view):
        # 사용자 인증 확인
        if not request.user or not request.user.is_authenticated:
            return False

        # Student 객체가 있는지 확인
        if not hasattr(request.user, "student"):
            return False

        student = request.user.student  # ✅ 올바르게 Student 객체 가져오기

        # 수강신청 확인
        if not Enrollment.objects.filter(student=student, is_active=True).exists():
            return False  # ✅ Response 대신 False 반환

        return True

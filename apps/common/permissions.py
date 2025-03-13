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


class IsActiveInstructor(BasePermission):
    """
    강사로 인증된 사용자(예: Is staff=True)는 모든 작업에 접근할 수 있도록 허용
    """

    message = "강사만 이 작업을 수행할 수 있습니다."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class IsActiveStudentOrInstructor(BasePermission):
    message = "수강 중인 학생 또는 강사만 이 작업을 수행할 수 있습니다."

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # 강사인 경우 바로 허용
        if request.user.is_staff:
            return True
        # 학생인 경우, 해당 학생이 활성 Enrollment를 가지고 있는지 확인
        if hasattr(request.user, "student"):
            return Enrollment.objects.filter(student=request.user.student, is_active=True).exists()
        return False

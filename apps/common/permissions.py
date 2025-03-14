from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

from apps.registrations.models import Enrollment
from apps.users.models import Student


class IsEnrolledStudent(BasePermission):
    """
    로그인한 사용자 중 수강신청이 승인된 학생만 접근 가능.
    """

    def has_permission(self, request, view):
        # 사용자 인증 확인
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("로그인이 필요한 서비스 입니다.")

        # Student 객체를 직접 조회
        student = Student.objects.filter(user=request.user).first()
        if not student:
            raise PermissionDenied("해당 강의를 수강 중인 학생만 접근할 수 있습니다.")  # 403 Forbidden 발생

        # 수강 신청 여부 확인
        if not Enrollment.objects.filter(student=student, is_active=True).exists():
            raise PermissionDenied("해당 강의를 수강 중인 학생만 접근할 수 있습니다.")  # 403 Forbidden 발생

        return True  # 모든 조건을 만족하면 접근 허용


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

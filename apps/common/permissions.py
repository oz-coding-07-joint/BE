from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from apps.registrations.models import Enrollment
from apps.users.models import User


class IsEnrolledStudent(BasePermission):
    """
    로그인한 사용자 중 수강신청이 승인된 학생만 접근 가능.
    """

    def has_permission(self, request, view):
        # 사용자 인증 확인
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("로그인이 필요한 서비스 입니다.")

        user = User.objects.select_related("student").filter(id=request.user.id).first()

        if not (user and user.student):  # 한 줄로 합쳐서 최적화
            raise PermissionDenied("학생만 접근할 수 있습니다.")

        student = user.student  # student 객체 안전하게 사용 가능

        # 수강 신청 여부 확인
        if not Enrollment.objects.filter(student=student, is_active=True).exists():
            raise PermissionDenied("해당 강의를 수강 중인 학생만 접근할 수 있습니다.")  # 403 Forbidden 발생

        return True  # 모든 조건을 만족하면 접근 허용


class IsActiveStudentOrInstructor(BasePermission):
    """수강 중인 학생 또는 강사 전용 접근 권한.

    로그인한 사용자 중에서 강사이거나,
    학생인 경우 수강 신청이 승인된 경우에만 접근을 허용.

    Attributes:
        message (str): 권한 거부 시 반환할 메시지.
    """
    message = "수강 중인 학생 또는 강사만 이 작업을 수행할 수 있습니다."

    def has_permission(self, request, view):
        """요청한 사용자에 대한 접근 권한을 판단.

        사용자가 로그인되어 있지 않으면 접근을 거부하고,
        강사이면 바로 접근을 허용하며,
        학생인 경우 활성화된 Enrollment가 있는지 확인.

        Args:
            request (Request): 요청 객체.
            view: 현재 실행 중인 뷰.

        Returns:
            bool: 접근 권한이 있으면 True, 없으면 False.
        """
        if not request.user or not request.user.is_authenticated:
            return False
        # 강사인 경우 바로 허용
        if hasattr(request.user, "instructor"):
            return True
        # 학생인 경우, 해당 학생이 활성 Enrollment를 가지고 있는지 확인
        if hasattr(request.user, "student"):
            return Enrollment.objects.filter(student=request.user.student, is_active=True).exists()
        return False

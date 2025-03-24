from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Enrollment
from .serializers import EnrollmentDetailSerializer, EnrollmentSerializer


class EnrollmentRegistrationView(APIView):
    """수강 신청 API.

    학생이 강의를 신청할 수 있도록 하는 엔드포인트.
    """

    @extend_schema(
        summary="수강 신청",
        description="학생이 강의를 신청하는 API입니다.",
        responses={
            201: OpenApiExample("성공 예시", value={"detail": "수강 신청 완료"}),
            400: OpenApiExample("오류 예시", value={"detail": "student_id is required"}),
            403: OpenApiExample("오류 예시", value={"detail": "학생만 수강 신청할 수 있습니다"}),
        },
        tags=["Enrollment"],
    )
    def post(self, request, course_id):
        """학생의 수강 신청을 처리.

        로그인한 사용자의 Student 인스턴스를 사용하며
        이미 수강 신청이 되어 있는지 확인 후 새 신청을 생성.

        Args:
            request (Request): 요청 객체.
            course_id (int): 신청할 강의의 식별자.

        Returns:
            Response: 수강 신청 완료 메시지 또는 오류 메시지를 포함한 응답.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(request.user, "student"):
            return Response({"detail": "학생만 수강 신청할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student

        if Enrollment.objects.filter(student=student, course=course_id).exists():
            return Response({"detail": "이미 수강 신청을 하셨습니다."}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "student": student.pk,
            "course": course_id,
            "is_active": False,  # 수강 신청 후 관리자가 승인하면 True로 처리
        }

        serializer = EnrollmentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "수강 신청 완료"}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class EnrollmentInProgressView(APIView):
    """수강 중인 수업 조회 API.

    현재 승인되어 수강 중인 수업 정보를 조회.
    """

    @extend_schema(
        summary="수강 중인 수업 조회",
        description="현재 수강 중인 수업을 조회합니다.",
        responses={
            200: EnrollmentDetailSerializer(many=True),
            404: OpenApiExample("오류 예시", value={"detail": "수강 중인 클래스가 없습니다."}),
        },
        tags=["Enrollment"],
    )
    def get(self, request):
        """현재 수강 중인 수업 목록을 조회.

        로그인한 사용자의 학생 정보를 확인한 후, 활성화된 수강 신청 정보를 반환.

        Args:
            request (Request): 요청 객체.

        Returns:
            Response: 수강 중인 수업의 직렬화된 목록 또는 오류 메시지를 포함한 응답.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(request.user, "student"):
            return Response({"detail": "학생 정보가 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student

        enrollments = Enrollment.objects.filter(is_active=True, student=student)
        if not enrollments.exists():
            return Response({"detail": "수강 중인 클래스가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EnrollmentDetailSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

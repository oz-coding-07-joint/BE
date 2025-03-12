from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Enrollment
from .serializers import EnrollmentDetailSerializer, EnrollmentSerializer


class EnrollmentRegistrationView(APIView):
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

    # 수강 신청
    def post(self, request, course_id):
        # 요청 데이터에서 student_id 대신, 로그인한 사용자의 Student 인스턴스를 사용
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # ForeignKey를 사용하므로 역참조 기본 이름은 student_set
        if not request.user.student_set.exists():
            return Response({"detail": "학생만 수강 신청할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        student = request.user.student_set.first()

        # 이미 해당 학생이 해당 강의에 등록되어 있는지 확인
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
    @extend_schema(
        summary="수강 중인 수업 조회",
        description="현재 수강 중인 수업을 조회합니다.",
        responses={
            200: EnrollmentDetailSerializer(many=True),
            404: OpenApiExample("오류 예시", value={"detail": "수강 중인 클래스가 없습니다."}),
        },
        tags=["Enrollment"],
    )
    # 수강중인 수업 조회
    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 학생 정보가 ForeignKey로 연결되어 있으므로, 역참조(student_set)를 사용
        if not request.user.student_set.exists():
            return Response({"detail": "학생 정보가 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        student = request.user.student_set.first()
        enrollments = Enrollment.objects.filter(is_active=True, student=student)
        if not enrollments.exists():
            return Response({"detail": "수강 중인 클래스가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EnrollmentDetailSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

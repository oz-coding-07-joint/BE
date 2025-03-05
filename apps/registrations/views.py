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
        request=EnrollmentSerializer,
        responses={
            201: OpenApiExample("성공 예시", value={"detail": "수강 신청 완료"}),
            400: OpenApiExample("오류 예시", value={"detail": "student_id is required"}),
        },
        tags=["Enrollment"],
    )

    # 수강 신청
    def post(self, request, course_id):
        # 요청 데이터에서 student_id 추출
        student_id = request.data.get("student_id")
        if not student_id:
            return Response({"detail": "student_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 해당 학생이 해당 강의에 등록되어 있는지 확인
        if Enrollment.objects.filter(student_id=student_id, course_id=course_id).exists():
            return Response({"detail": "이미 수강 신청을 하셨습니다."}, status=status.HTTP_400_BAD_REQUEST)

        data = {
            "student": student_id,
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
        request=EnrollmentDetailSerializer,
        responses={
            200: EnrollmentDetailSerializer(many=True),
            404: OpenApiExample("오류 예시", value={"detail": "수강 중인 클래스가 없습니다."}),
        },
        tags=["Enrollment"],
    )
    # 수강중인 수업 조회
    def get(self, request):
        """
        승인 대기, 취소된 등을 가져올 수 있으므로
        현재 수강 중인 수업만 조회하려면 필요
        """
        enrollments = Enrollment.objects.filter(is_active=True)
        if not enrollments.exists():
            return Response({"detail": "수강 중인 클래스가 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = EnrollmentDetailSerializer(enrollments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

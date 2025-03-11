from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.courses.models import Lecture
from apps.registrations.models import Enrollment

from .models import Review
from .serializers import ReviewDetailSerializer, ReviewSerializer


class ReviewView(APIView):

    def get_authenticators(self):
        if not hasattr(self, "request") or self.request is None:
            return super().get_authenticators()
        if self.request.method == "GET":
            return []  # GET 요청은 인증하지 않음
        return [JWTAuthentication()]

    def get_permissions(self):
        if self.request.method == "GET":
            return [AllowAny()]  # GET 요청은 모든 사용자 허용
        return super().get_permissions()

    @extend_schema(
        summary="수업 후기 조회",
        description=("특정 강의에 대한 후기를 조회합니다."),
        responses={
            200: ReviewSerializer(many=True),
            404: OpenApiExample("후기 없음", value={"error": "강의 후기를 찾을 수 없습니다"}),
        },
        tags=["Review"],
    )
    # 수업 후기 조회
    def get(self, request, lecture_id):
        reviews = Review.objects.filter(lecture_id=lecture_id)
        if reviews.exists():
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "강의 후기를 찾을 수 없습니다"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="후기 등록",
        description="강의에 대한 후기를 등록합니다.",
        request=ReviewSerializer,
        responses={
            201: OpenApiExample("성공 예시", value={"detail": "리뷰 등록 완료"}),
            400: OpenApiExample("오류 예시", value={"detail": "유효하지 않은 데이터입니다."}),
        },
        tags=["Review"],
    )
    # 후기 등록
    def post(self, request, lecture_id):
        # 강의 객체를 가져와서 수강 여부 확인에 사용
        try:
            lecture = Lecture.objects.get(id=lecture_id)
        except Lecture.DoesNotExist:
            return Response({"detail": "해당 강의를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 로그인한 사용자의 Student 인스턴스 가져오기 (ForeignKey 사용 시 역참조: student_set)
        if not request.user.student_set.exists():
            return Response({"detail": "학생만 후기를 등록할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student_set.first()

        # 해당 강의를 수강 중인 학생인지 확인 (Enrollment에서 is_active=True)
        if not Enrollment.objects.filter(student=student, course=lecture.course, is_active=True).exists():
            return Response(
                {"detail": "해당 강의를 수강 중인 학생만 후기를 등록할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 한 강의당 한 번만 후기를 작성할 수 있도록 체크
        if Review.objects.filter(lecture=lecture, student=student).exists():
            return Response(
                {"detail": "한 강의당 한 번만 후기를 작성할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["lecture"] = lecture_id
        data["student"] = student.pk

        serializer = ReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "리뷰 등록 완료"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class MyReviewListView(APIView):
    @extend_schema(
        summary="내가 작성한 후기 조회",
        description="현재 로그인한 사용자가 작성한 후기를 조회합니다.",
        responses={200: ReviewDetailSerializer(many=True)},
        tags=["Review"],
    )
    # 내가 작성한 후기 조회
    def get(self, request):
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not request.user.student_set.exists():
            return Response({"detail": "학생 정보가 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student_set.first()

        reviews = Review.objects.filter(student=student)
        if reviews.exists():
            serializer = ReviewDetailSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성한 후기가 없습니다"}, status=status.HTTP_404_NOT_FOUND)

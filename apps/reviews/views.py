from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.courses.models import Lecture
from apps.registrations.models import Enrollment

from .models import Review
from .serializers import (
    ReviewCreateSerializer,
    ReviewDetailSerializer,
    ReviewSerializer,
)


class ReviewView(APIView):
    """수업 후기 조회 및 등록 API.

    GET 요청은 특정 강의의 후기를 조회하며, POST 요청은 후기를 등록.
    인증은 POST 요청에만 적용.
    """

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
    def get(self, request, lecture_id):
        """특정 강의의 후기를 조회.

        Args:
            request (Request): 요청 객체.
            lecture_id (int): 후기를 조회할 강의의 식별자.

        Returns:
            Response: 후기가 존재할 경우 직렬화된 데이터, 없으면 오류 메시지.
        """
        reviews = Review.objects.filter(lecture_id=lecture_id)
        if reviews.exists():
            serializer = ReviewSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "강의 후기를 찾을 수 없습니다"}, status=status.HTTP_404_NOT_FOUND)

    @extend_schema(
        summary="후기 등록",
        description="강의에 대한 후기를 등록합니다.",
        request=ReviewCreateSerializer,
        responses={
            201: OpenApiExample("성공 예시", value={"detail": "리뷰 등록 완료"}),
            400: OpenApiExample("오류 예시", value={"detail": "유효하지 않은 데이터입니다."}),
        },
        tags=["Review"],
    )
    def post(self, request, lecture_id):
        """강의 후기를 등록.

        - 수강 중인 학생만 후기를 등록할 수 있음.
        - 한 강의당 한 번만 후기를 작성할 수 있음.

        Args:
            request (Request): 요청 객체.
            lecture_id (int): 후기를 등록할 강의의 식별자.

        Returns:
            Response: 리뷰 등록 성공 또는 오류 메시지를 포함한 응답.
        """
        try:
            lecture = Lecture.objects.get(id=lecture_id)
        except Lecture.DoesNotExist:
            return Response({"detail": "해당 강의를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        if not hasattr(request.user, "student"):
            return Response({"detail": "학생만 후기를 등록할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student

        if not Enrollment.objects.filter(student=student, course=lecture.course, is_active=True).exists():
            return Response(
                {"detail": "해당 강의를 수강 중인 학생만 후기를 등록할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN
            )

        if Review.objects.filter(lecture=lecture, student=student).exists():
            return Response(
                {"detail": "한 강의당 한 번만 후기를 작성할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ReviewCreateSerializer(data=request.data, context={"lecture": lecture, "student": student})
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "리뷰 등록 완료"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class MyReviewListView(APIView):
    """내가 작성한 후기 조회 API.

    현재 로그인한 사용자가 작성한 후기를 반환.
    """

    @extend_schema(
        summary="내가 작성한 후기 조회",
        description="현재 로그인한 사용자가 작성한 후기를 조회합니다.",
        responses={200: ReviewDetailSerializer(many=True)},
        tags=["Review"],
    )
    def get(self, request):
        """로그인한 학생이 작성한 후기를 조회.

        Args:
            request (Request): 요청 객체.

        Returns:
            Response: 후기가 존재할 경우 직렬화된 데이터 없으면 오류 메시지.
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"detail": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        if not hasattr(request.user, "student"):
            return Response({"detail": "학생 정보가 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        student = request.user.student

        reviews = Review.objects.filter(student=student)
        if reviews.exists():
            serializer = ReviewDetailSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성한 후기가 없습니다"}, status=status.HTTP_404_NOT_FOUND)

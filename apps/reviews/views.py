from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.courses.models import Lecture
from apps.registrations.models import Enrollment

from .models import Review
from .serializers import ReviewDetailSerializer, ReviewSerializer


class ReviewView(APIView):
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

        # 해당 강의의 수강중인 학생인지 확인 (Enrollment에서 is_active=True)
        if not Enrollment.objects.filter(student=request.user, course=lecture.course, is_active=True).exists():
            return Response(
                {"detail": "해당 강의를 수강 중인 학생만 후기를 등록할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 이미 후기를 작성한 경우, 한 강의당 한 번만 작성 가능하도록 체크
        if Review.objects.filter(lecture=lecture, student=request.user).exists():
            return Response(
                {"detail": "한 강의당 한 번만 후기를 작성할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = request.data.copy()
        data["lecture"] = lecture_id
        data["student"] = request.user.id

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
        # 인증된 사용자의 리뷰만 필터링 (User 모델과 연결된 student 필드 기준)
        reviews = Review.objects.filter(student=request.user)
        if reviews.exists():
            serializer = ReviewDetailSerializer(reviews, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "작성한 후기가 없습니다"}, status=status.HTTP_404_NOT_FOUND)

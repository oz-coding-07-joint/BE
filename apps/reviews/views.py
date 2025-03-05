from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Review
from .serializers import ReviewDetailSerializer, ReviewSerializer


class ReviewView(APIView):
    @extend_schema(
        summary="수업 후기 조회",
        description=("특정 강의에 대한 후기를 조회합니다."),
        responses={
            200: ReviewDetailSerializer(many=True),
            404: OpenApiExample("후기 없음", value={"error": "강의 후기를 찾을 수 없습니다"}),
        },
        tags=["Review"],
    )
    # 수업 후기 조회
    def get(self, request, lecture_id):
        reviews = Review.objects.filter(lecture_id=lecture_id)
        if reviews.exists():
            serializer = ReviewDetailSerializer(reviews, many=True)
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
        data = request.data.copy()
        data["lecture"] = lecture_id  # URL로부터 전달받은 lecture_id를 데이터에 추가
        serializer = ReviewSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "리뷰 등록 완료"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

from django.core.cache import cache
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assignment, AssignmentComment
from .serializers import AssignmentCommentSerializer, AssignmentSerializer


class AssignmentView(APIView):
    @extend_schema(
        summary="강의 챕터별 과제 목록 조회",
        description="lecture_chapter_id와 연결된 과제들을 조회합니다.",
        responses={
            200: AssignmentSerializer(many=True),
            401: OpenApiExample("오류 예시", value={"error": "잘못된 lecture_chapter_id 입니다."}),
        },
        tags=["Assignment"],
    )
    # 강의 챕터별 과제 목록 조회
    def get(self, request, lecture_chapter_id):
        if lecture_chapter_id <= 0:
            return Response({"error": "잘못된 lecture_chapter_id 입니다."}, status=status.HTTP_401_UNAUTHORIZED)

        # Redis 캐시를 사용하여 조회 결과를 캐싱
        cache_key = f"assignments_{lecture_chapter_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            assignments_data = cached_data
        else:
            # 데이터베이스에서 ChapterVideo의 lecture_chapter_id가 lecture_chapter_id와 일치하는 과제들을 조회
            assignments = Assignment.objects.filter(chapter_video__lecture_chapter_id=lecture_chapter_id)
            serializer = AssignmentSerializer(assignments, many=True)
            assignments_data = serializer.data
            # 캐시에 10분 동안 저장 (600초)
            cache.set(cache_key, assignments_data, 600)

        return Response(
            {"lecture_chapter_id": lecture_chapter_id, "assignments": assignments_data},
            status=status.HTTP_200_OK
        )


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class AssignmentCommentView(APIView):
    @extend_schema(
        summary="수강생 과제 및 피드백 목록 조회",
        description="부모가 없는 최상위 댓글만 조회합니다.",
        responses={
            200: AssignmentCommentSerializer(many=True),
            400: OpenApiExample("오류 예시", value={"error": "유효하지 않은 요청입니다."}),
        },
        tags=["Assignment"],
    )
    # 수강생 과제 및 피드백 목록 조회
    def get(self, request, assignment_id):
        """
        학생이 제출한 과제는 정적으로 조회,
        과제 피드백은 시리얼라이저 내의 replies 필드로 동적으로 처리
        """
        if not request.user or not request.user.is_authenticated:
            return Response({"error": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        comments = AssignmentComment.objects.filter(parent__isnull=True, user=request.user)
        serializer = AssignmentCommentSerializer(comments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="강의 과제 제출",
        description="assignment_id를 통해 과제가 존재하는지 확인하고, 과제 제출을 처리합니다.",
        request=AssignmentCommentSerializer,
        responses={
            201: OpenApiExample(
                "성공 예시",
                value={"detail": "과제 제출이 완료 되었습니다."},
            ),
            404: OpenApiExample(
                "과제 없음",
                value={"detail": "해당 과제를 찾을 수 없습니다."},
            ),
            400: OpenApiExample(
                "오류 예시",
                value={"detail": "유효하지 않은 데이터입니다."},
            ),
        },
        tags=["Assignment"],
    )
    # 강의 과제 제출
    def post(self, request, assignment_id):
        if not request.user or not request.user.is_authenticated:
            return Response({"error": "유효하지 않은 요청입니다."}, status=status.HTTP_400_BAD_REQUEST)

        # assignment_id를 통해 과제가 존재하는지 확인
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "해당 과제를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        data["assignment"] = assignment.id
        data["user"] = request.user.id

        if data.get("parent"):
            if not request.user.is_staff:
                return Response({"detail": "대댓글 작성은 강사만 가능합니다."}, status=status.HTTP_403_FORBIDDEN)

        serializer = AssignmentCommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "과제 제출이 완료 되었습니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

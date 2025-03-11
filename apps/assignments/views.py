import json

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.utils import redis_client

from .models import Assignment, AssignmentComment
from .serializers import AssignmentCommentSerializer, AssignmentSerializer, AssignmentCommentCreateSerializer


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

        cache_key = f"assignments_{lecture_chapter_id}"
        cached_data = redis_client.get(cache_key)

        if cached_data:
            # Redis에 저장된 JSON 문자열을 파싱하여 Python 객체로 변환
            assignments_data = json.loads(cached_data)
        else:
            # ChapterVideo의 lecture_chapter_id가 lecture_chapter_id와 일치하는 과제들을 조회
            assignments = Assignment.objects.filter(chapter_video__lecture_chapter_id=lecture_chapter_id)
            serializer = AssignmentSerializer(assignments, many=True)
            assignments_data = serializer.data
            # 데이터를 JSON 문자열로 변환 후 Redis에 600초(10분) 동안 저장
            redis_client.setex(cache_key, 600, json.dumps(assignments_data))

        return Response(
            {"lecture_chapter_id": lecture_chapter_id, "assignments": assignments_data}, status=status.HTTP_200_OK
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

        if request.user.is_staff:
            # 강사는 해당 과제에 속한 모든 최상위 댓글을 조회
            comments = AssignmentComment.objects.filter(parent__isnull=True, assignment=assignment_id)
        else:
            # 학생은 본인이 작성한 최상위 댓글만 조회
            comments = AssignmentComment.objects.filter(
                parent__isnull=True, assignment=assignment_id, user=request.user
            )

        serializer = AssignmentCommentSerializer(comments, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="강의 과제 제출",
        description="assignment_id를 통해 과제가 존재하는지 확인하고, 과제 제출을 처리합니다.",
        request=AssignmentCommentCreateSerializer,
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

        # 대댓글 작성은 강사가 아니면 불허
        if request.data.get("parent") and not request.user.is_staff:
            return Response({"detail": "대댓글 작성은 강사만 가능합니다."}, status=status.HTTP_403_FORBIDDEN)

        # 클라이언트는 content와 file_url만 전송하도록 하고,
        # assignment와 user 정보는 context로 전달합니다.
        data = request.data.copy()

        serializer = AssignmentCommentCreateSerializer(
            data=data, context={"assignment": assignment, "user": request.user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "과제 제출이 완료 되었습니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
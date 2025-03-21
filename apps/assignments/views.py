import json

from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsActiveStudentOrInstructor
from apps.common.utils import redis_client

from .models import Assignment, AssignmentComment
from .serializers import (
    AssignmentCommentCreateSerializer,
    AssignmentCommentSerializer,
    AssignmentSerializer,
)


class AssignmentView(APIView):
    """강의 챕터별 과제 목록 조회 API.

    수강 중인 학생 또는 강사만 접근할 수 있도록 IsActiveStudentOrInstructor 퍼미션을 사용.
    """

    permission_classes = [IsActiveStudentOrInstructor]

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
        """lecture_chapter_id를 기반으로 과제 목록을 조회.

        캐싱(Redis)을 사용하여 조회 성능을 개선.

        Args:
            request (Request): 요청 객체.
            lecture_chapter_id (int): 강의 챕터의 식별자.

        Returns:
            Response: 과제 목록과 lecture_chapter_id를 포함한 응답.
        """
        if lecture_chapter_id <= 0:
            return Response({"error": "잘못된 lecture_chapter_id 입니다."}, status=status.HTTP_400_BAD_REQUEST)

        cache_key = f"assignments_{lecture_chapter_id}"
        cached_data = redis_client.get(cache_key)

        if cached_data:
            assignments_data = json.loads(cached_data)
        else:
            # lecture_chapter_id에 연결된 과제들을 조회
            assignments = Assignment.objects.filter(chapter_video__lecture_chapter__id=lecture_chapter_id)
            serializer = AssignmentSerializer(assignments, many=True)
            assignments_data = serializer.data
            CACHE_TIMEOUT = 5 * 3600
            redis_client.setex(cache_key, CACHE_TIMEOUT, json.dumps(assignments_data))

        return Response(
            {"lecture_chapter_id": lecture_chapter_id, "assignments": assignments_data},
            status=status.HTTP_200_OK,
        )


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class AssignmentCommentView(APIView):
    """과제 제출 및 피드백 API.

    GET 요청: 수강생 또는 강사가 과제 관련 최상위 댓글 및 피드백 조회.
    POST 요청: 강의 과제 제출 (학생은 대댓글 작성 불가).
    """

    permission_classes = [IsActiveStudentOrInstructor]

    @extend_schema(
        summary="수강생 과제 및 피드백 목록 조회",
        description="부모가 없는 최상위 댓글만 조회합니다.",
        responses={
            200: AssignmentCommentSerializer(many=True),
            400: OpenApiExample("오류 예시", value={"error": "유효하지 않은 요청입니다."}),
        },
        tags=["Assignment"],
    )
    def get(self, request, assignment_id):
        """특정 과제의 최상위 댓글을 조회.

        강사인 경우 모든 댓글을 조회하고, 학생인 경우 자신이 작성한 댓글만 조회.

        Args:
            request (Request): 요청 객체.
            assignment_id (int): 과제의 식별자.

        Returns:
            Response: 직렬화된 댓글 목록.
        """
        if hasattr(request.user, "instructor"):
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
            201: OpenApiExample("성공 예시", value={"detail": "과제 제출이 완료 되었습니다."}),
            404: OpenApiExample("과제 없음", value={"detail": "해당 과제를 찾을 수 없습니다."}),
            400: OpenApiExample("오류 예시", value={"detail": "유효하지 않은 데이터입니다."}),
            403: OpenApiExample("오류 예시", value={"detail": "수강 중인 학생만 과제 제출이 가능합니다."}),
        },
        tags=["Assignment"],
    )
    def post(self, request, assignment_id):
        """특정 과제에 대해 과제 제출을 처리.

        - 강사는 대댓글 작성이 가능하며 학생은 대댓글 작성이 불가능.
        - 요청 데이터는 클라이언트에서 content, file_url, parent만 전송하며
          assignment와 request.user 정보는 context를 통해 전달.

        Args:
            request (Request): 요청 객체.
            assignment_id (int): 과제의 식별자.

        Returns:
            Response: 과제 제출 성공 또는 오류 메시지를 포함한 응답.

        Raises:
            Response with HTTP_404_NOT_FOUND: 과제를 찾을 수 없는 경우.
            Response with HTTP_403_FORBIDDEN: 학생이 대댓글을 작성하려 할 때.
            Response with HTTP_400_BAD_REQUEST: 직렬화된 데이터에 오류가 있는 경우.
        """
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "해당 과제를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        if request.data.get("parent") and not hasattr(request.user, "instructor"):
            return Response({"detail": "대댓글 작성은 강사만 가능합니다."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data.copy()
        serializer = AssignmentCommentCreateSerializer(
            data=data, context={"assignment": assignment, "user": request.user}
        )
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "과제 제출이 완료 되었습니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

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
    # 수강 중인 학생 또는 강사만 접근할 수 있음.
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
        if lecture_chapter_id <= 0:
            return Response({"error": "잘못된 lecture_chapter_id 입니다."}, status=status.HTTP_401_UNAUTHORIZED)

        cache_key = f"assignments_{lecture_chapter_id}"
        cached_data = redis_client.get(cache_key)

        if cached_data:
            assignments_data = json.loads(cached_data)
        else:
            # lecture_chapter_id에 연결된 과제들을 조회
            assignments = Assignment.objects.filter(chapter_video__lecture_chapter__id=lecture_chapter_id)
            serializer = AssignmentSerializer(assignments, many=True)
            assignments_data = serializer.data
            redis_client.setex(cache_key, 18000, json.dumps(assignments_data))

        return Response(
            {"lecture_chapter_id": lecture_chapter_id, "assignments": assignments_data},
            status=status.HTTP_200_OK,
        )


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class AssignmentCommentView(APIView):
    # 수강 중인 학생 또는 강사만 접근할 수 있음.
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
    # 수강생 과제 및 피드백 목록 조회
    def get(self, request, assignment_id):
        """
        학생이 제출한 과제는 정적으로 조회,
        과제 피드백은 시리얼라이저 내의 replies 필드로 동적으로 처리
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
    # 강의 과제 제출
    def post(self, request, assignment_id):
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "해당 과제를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 강사는 대댓글 작성이 가능하지만, 학생은 대댓글 작성 불가
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

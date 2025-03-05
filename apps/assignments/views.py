from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Assignment, AssignmentComment
from .serializers import AssignmentCommentSerializer, AssignmentSerializer


class AssignmentView(APIView):
    @extend_schema(
        summary="강의 챕터별 과제 목록 조회",
        description="chapter_video_id와 연결된 과제들을 조회합니다.",
        responses={200: AssignmentSerializer(many=True)},
        tags=["Assignment"],
    )
    # 강의 챕터별 과제 목록 조회
    def get(self, request, chapter_video_id):
        # chapter_video_id와 연결된 과제들을 조회
        assignments = Assignment.objects.filter(chapter_video_id=chapter_video_id)
        serializer = AssignmentSerializer(assignments, many=True)
        return Response(
            {"chapter_video_id": chapter_video_id, "assignments": serializer.data}, status=status.HTTP_200_OK
        )


# -----------------------------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------------------------


class AssignmentCommentView(APIView):
    @extend_schema(
        summary="수강생 과제 및 피드백 목록 조회",
        description="부모가 없는 최상위 댓글만 조회합니다.",
        responses={200: AssignmentCommentSerializer(many=True)},
        tags=["Assignment"],
    )
    # 수강생 과제 및 피드백 목록 조회
    def get(self, request):
        """
        학생이 제출한 과제는 정적으로 조회,
        과제 피드백은 시리얼라이저 내의 replies 필드로 동적으로 처리
        """
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
        # assignment_id를 통해 과제가 존재하는지 확인
        try:
            assignment = Assignment.objects.get(id=assignment_id)
        except Assignment.DoesNotExist:
            return Response({"detail": "해당 과제를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 요청 데이터에 assignment ID 추가
        data = request.data.copy()
        data["assignment"] = assignment.id

        serializer = AssignmentCommentSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({"detail": "과제 제출이 완료 되었습니다."}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

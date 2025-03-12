from django.conf import settings
from django.shortcuts import redirect
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsActiveStudent
from apps.courses.models import ChapterVideo, Lecture, LectureChapter, ProgressTracking
from apps.courses.serializers import (
    ChapterVideoSerializer,
    LectureChapterSerializer,
    LectureDetailSerializer,
    LectureListSerializer,
    ProgressTrackingSerializer,
    ProgressTrackingUpdateSerializer,
)
from apps.registrations.models import Enrollment


class LectureListView(APIView):
    """수강 신청 후 승인된 학생만 접근 가능한 과목 목록 조회"""

    permission_classes = [IsAuthenticated, IsActiveStudent]  # 인증된 사용자만 접근 가능

    @extend_schema(
        summary="과목 목록 조회",
        description="와이어프레임의 수업자료 페이지 입니다. 수강 신청 후 승인된 학생만 자신의 과목 목록을 조회할 수 있습니다. 승인되지 않은 사용자는 강의소개 페이지로 리다이렉트됩니다.",
        responses={
            200: LectureListSerializer(many=True),
            302: OpenApiResponse(description="수강 승인되지 않은 사용자 → 강의 소개 페이지로 리다이렉트"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request):
        try:
            student = request.user.student
            lectures = Lecture.objects.filter(enrollment__user=request.user, enrollment__is_active=True)
            serializer = LectureListSerializer(lectures, many=True, context={"request": request})
            return Response({"student_id": student.id, "lectures": serializer.data}, status=200)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LectureDetailView(APIView):
    """과목 상세 조회 (수업정보)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="과목 상세 조회",
        description="특정 과목의 상세 정보를 조회합니다. 와이어프레임의 수업정보 모달입니다. 과목 정보와 강사의 정보를 출력합니다.",
        responses={
            200: LectureDetailSerializer,
            404: OpenApiResponse(description="해당 과목을 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, lecture_id):
        try:
            lecture = Lecture.objects.get(id=lecture_id)
            serializer = LectureDetailSerializer(lecture)
            return Response(serializer.data)
        except Lecture.DoesNotExist:
            return Response({"error": "해당 과목을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)


class LectureChapterListView(APIView):
    """과목의 챕터 및 강의 영상 제목 목록 조회 (수업 목록 드롭다운)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="과목의 챕터 및 강의 영상 제목 목록 조회",
        description="특정 과목의 챕터 목록과 해당 강의 영상 제목을 조회합니다. 와이어 프레임의 수업 자료 상세 페이지 입니다. ",
        responses={
            200: LectureChapterSerializer(many=True),
            404: OpenApiResponse(description="해당 챕터를 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, lecture_id):
        try:
            chapters = LectureChapter.objects.filter(lecture_id=lecture_id)
            if not chapters.exists():
                return Response({"error": "해당 챕터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            serializer = LectureChapterSerializer(chapters, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoProgressView(APIView):
    """강의 영상 학습 진행률 조회 (chapter_video)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 조회",
        description="사용자의 특정 강의 영상에 대한 학습 진행률을 조회합니다. 이어보기 기능을 제공할 예정입니다.",
        responses={
            200: ProgressTrackingSerializer,
            404: OpenApiResponse(description="진행 데이터를 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, student_id, chapter_video_id):
        try:
            progress = ProgressTracking.objects.get(student_id=student_id, chapter_video_id=chapter_video_id)
            serializer = ProgressTrackingSerializer(progress)
            return Response(serializer.data)
        except ProgressTracking.DoesNotExist:
            return Response({"error": "진행 데이터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)


class ChapterVideoProgressUpdateView(APIView):
    """강의 영상 학습 완료 표시 API (PATCH)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="강의 영상 학습 완료 표시",
        description="특정 강의 영상의 학습 진행률을 수정합니다. 시청 완료 표시(`is_completed=True`)에 사용됩니다.",
        request=ProgressTrackingUpdateSerializer,
        responses={
            200: ProgressTrackingSerializer,
            400: OpenApiResponse(description="잘못된 요청 데이터"),
            404: OpenApiResponse(description="진행 데이터를 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def patch(self, request, chapter_video_id):
        try:
            progress_tracking = ProgressTracking.objects.get(
                chapter_video_id=chapter_video_id, student=request.user.student
            )
        except ProgressTracking.DoesNotExist:
            return Response({"error": "진행 데이터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProgressTrackingUpdateSerializer(progress_tracking, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(ProgressTrackingSerializer(progress_tracking).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChapterVideoDetailView(APIView):
    """
    강의 영상 상세 조회 (chapter_video)
    """

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="강의 영상 상세 조회",
        description="특정 강의 영상의 상세 정보를 조회합니다. 영상 시청을 의미합니다.",
        responses={
            200: ChapterVideoSerializer,
            404: OpenApiResponse(description="해당 강의 영상을 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, chapter_video_id):
        try:
            video = ChapterVideo.objects.get(id=chapter_video_id)
            serializer = ChapterVideoSerializer(video)
            return Response(serializer.data)
        except ChapterVideo.DoesNotExist:
            return Response({"error": "해당 강의 영상을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

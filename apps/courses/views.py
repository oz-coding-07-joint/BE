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
    ProgressTrackingCreateSerializer,
    ProgressTrackingSerializer,
    ProgressTrackingUpdateSerializer,
)
from apps.users.models import Student


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
        # Student 객체 가져오기
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"error": "학생 계정이 아닙니다."}, status=403)

        # 수강 신청된 강의 목록 조회
        lectures = Lecture.objects.filter(course__enrollment__student=student, course__enrollment__is_active=True)

        if not lectures.exists():
            # 수강 신청이 안 되어 있으면 랜딩 페이지로 리디렉션
            return Response({"redirect_url": "https://dummy-landing-page.com"}, status=302)

        # Serializer 변환 후 반환
        serializer = LectureListSerializer(lectures, many=True, context={"request": request})
        return Response({"student_id": student.id, "lectures": serializer.data}, status=200)


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
            lecture = Lecture.objects.select_related("instructor__user").get(id=lecture_id)
            serializer = LectureDetailSerializer(lecture)
            return Response(serializer.data, status=status.HTTP_200_OK)
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


class ChapterVideoProgressCreateView(APIView):
    """강의 영상 학습 진행률 생성 API (POST)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 생성",
        description="특정 강의 영상(chapter_video)에 대한 학습 진행 데이터를 생성합니다. 해당 데이터가 없다면 새로 생성합니다.",
        request=ProgressTrackingCreateSerializer,
        responses={
            201: ProgressTrackingSerializer,
            400: OpenApiResponse(description="잘못된 요청 데이터"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def post(self, request, chapter_video_id):
        try:
            student = Student.objects.get(user=request.user)  # 현재 로그인한 사용자의 Student 객체 찾기

            # ProgressTracking 데이터가 이미 존재하는지 확인
            progress_tracking, created = ProgressTracking.objects.get_or_create(
                student=student,
                chapter_video_id=chapter_video_id,  # URL에서 받은 chapter_video_id 사용
                defaults={"progress": 0.0, "is_completed": False},  # 기본값 설정
            )

            # 존재하는 경우 바로 반환
            if not created:
                return Response({"message": "이미 진행 데이터가 존재합니다."}, status=status.HTTP_200_OK)

            # 새로 생성한 경우 Serializer를 이용해 응답
            serializer = ProgressTrackingCreateSerializer(progress_tracking)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Student.DoesNotExist:
            return Response({"error": "학생 계정을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class ChapterVideoProgressUpdateView(APIView):
    """강의 영상 학습 진행률 업데이트 API (PATCH)"""

    permission_classes = [IsAuthenticated, IsActiveStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 업데이트",
        description="특정 강의 영상(chapter_video)의 학습 진행률을 수정합니다. 처음 학습한 경우에는 먼저 POST 요청을 보내야 합니다.",
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
            student = Student.objects.get(user=request.user)  # 현재 로그인한 사용자 찾기
            progress_tracking = ProgressTracking.objects.get(student=student, chapter_video_id=chapter_video_id)

            serializer = ProgressTrackingUpdateSerializer(progress_tracking, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(ProgressTrackingSerializer(progress_tracking).data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Student.DoesNotExist:
            return Response({"error": "학생 계정을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except ProgressTracking.DoesNotExist:
            return Response({"error": "진행 데이터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)


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

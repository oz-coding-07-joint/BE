import json

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsEnrolledStudent
from apps.common.utils import generate_ncp_signed_url, redis_client
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

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="과목 목록 조회",
        description="수강 신청 후 승인된 학생만 자신의 과목 목록을 조회할 수 있습니다.",
        responses={
            200: LectureListSerializer(many=True),
            302: OpenApiResponse(description="수강 승인되지 않은 사용자 → 강의 소개 페이지로 리다이렉트"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request):
        student = Student.objects.filter(user=request.user).first()
        if not student:
            return Response({"error": "학생 계정이 아닙니다."}, status=403)

        lectures = Lecture.objects.filter(course__enrollment__student=student, course__enrollment__is_active=True)
        if not lectures.exists():
            return Response({"redirect_url": "https://dummy-landing-page.com"}, status=302)

        response_data = []
        for lecture in lectures:
            chapter_videos = ChapterVideo.objects.filter(lecture_chapter__lecture=lecture)
            total_videos = chapter_videos.count()
            completed_videos = chapter_videos.filter(
                progresstracking__student=student, progresstracking__is_completed=True
            ).count()
            progress_rate = (completed_videos / total_videos) * 100 if total_videos > 0 else 0

            serialized_lecture = LectureListSerializer(lecture, context={"request": request}).data
            serialized_lecture["progress_rate"] = progress_rate
            response_data.append(serialized_lecture)

        return Response({"student_id": student.id, "lectures": response_data}, status=200)


class LectureDetailView(APIView):
    """과목 상세 조회 (수업정보)"""

    permission_classes = [IsEnrolledStudent]

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

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="과목의 챕터 및 강의 영상 제목 목록 조회",
        description="특정 과목의 챕터 목록과 해당 강의 영상 제목을 조회합니다. 와이어프레임의 수업 자료 상세 페이지입니다.",
        responses={
            200: LectureChapterSerializer(many=True),
            404: OpenApiResponse(description="해당 챕터를 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, lecture_id):
        try:
            cache_key = f"lecture_chapters:{lecture_id}"  # Redis 키 설정
            cached_data = redis_client.get(cache_key)

            if cached_data:
                # Redis에서 데이터가 존재하면 그대로 반환
                return Response(json.loads(cached_data), status=status.HTTP_200_OK)

            # Redis에 데이터가 없으면 DB 조회
            chapters = LectureChapter.objects.filter(lecture_id=lecture_id)
            if not chapters.exists():
                return Response({"error": "해당 챕터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            serializer = LectureChapterSerializer(chapters, many=True)
            response_data = serializer.data

            # Redis에 캐싱 (다섯시간)
            redis_client.setex(cache_key, 18000, json.dumps(response_data))

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoProgressCreateView(APIView):
    """강의 영상 학습 진행률 생성 API (POST)"""

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 생성",
        description="특정 강의 영상(chapter_video)에 대한 학습 진행 데이터를 생성합니다.",
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
            student = Student.objects.get(user=request.user)
            chapter_video = ChapterVideo.objects.get(id=chapter_video_id)

            serializer = ProgressTrackingCreateSerializer(
                data=request.data, context={"request": request, "chapter_video_id": chapter_video_id}  #  context 추가
            )
            serializer.is_valid(raise_exception=True)
            progress_tracking = serializer.save()

            return Response(ProgressTrackingSerializer(progress_tracking).data, status=status.HTTP_201_CREATED)

        except Student.DoesNotExist:
            return Response({"error": "학생 계정을 찾을 수 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        except ChapterVideo.DoesNotExist:
            return Response({"error": "해당 강의 영상을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoProgressUpdateView(APIView):
    """강의 영상 학습 진행률 업데이트 API (PATCH)"""

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 업데이트",
        description="특정 강의 영상(chapter_video)의 학습 진행률을 수정합니다. total_duration 값은 프론트에서 제공해야 합니다.",
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
            student = Student.objects.get(user=request.user)
            progress_tracking = ProgressTracking.objects.get(student=student, chapter_video_id=chapter_video_id)

            serializer = ProgressTrackingUpdateSerializer(
                progress_tracking,
                data=request.data,
                context={"request": request},  #  total_duration을 전달하기 위해 context 추가
            )
            serializer.is_valid(raise_exception=True)
            progress_tracking = serializer.save()

            return Response(ProgressTrackingSerializer(progress_tracking).data, status=status.HTTP_200_OK)

        except ProgressTracking.DoesNotExist:
            return Response(
                {"error": "진행 데이터를 찾을 수 없습니다. 먼저 POST 요청을 보내주세요."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoDetailView(APIView):
    """
    강의 영상 상세 조회 (chapter_video) - S3 Pre-signed URL 적용
    """

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="강의 영상 상세 조회 (S3 Pre-signed URL)",
        description="특정 강의 영상의 상세 정보를 조회합니다. 일정 시간 동안 접근 가능한 Signed URL을 반환합니다.",
        responses={
            200: ChapterVideoSerializer,
            404: OpenApiResponse(description="해당 강의 영상을 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, chapter_video_id):
        try:
            student = Student.objects.get(user=request.user)
            video = ChapterVideo.objects.get(id=chapter_video_id)

            # Referrer 확인 (일부 요청에는 HTTP_REFERER가 없을 수 있음)
            allowed_referrers = [
                "https://umdoong.shop",
                "https://api.umdoong.shop",
                "http://localhost:8000",
                "http://localhost:3000",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:3000",
            ]
            referrer = request.META.get("HTTP_REFERER", "")

            if referrer and not any(referrer.startswith(allowed) for allowed in allowed_referrers):
                return Response({"error": "잘못된 접근입니다."}, status=status.HTTP_403_FORBIDDEN)

            # 사용자 인증 기반 Signed URL 생성
            signed_url = generate_ncp_signed_url(video.video_url.name, student.id)

            response_data = {
                "id": video.id,
                "title": video.title,
                "video_url": signed_url,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ChapterVideo.DoesNotExist:
            return Response({"error": "해당 강의 영상을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

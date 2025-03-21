import json

from django.core.cache import cache
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
)
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsEnrolledStudent
from apps.common.utils import (
    generate_material_signed_url,
    generate_ncp_signed_url,
    redis_client,
)
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
        student = request.user.student

        # Redis 캐싱 키 설정
        cache_key = f"student_{student.id}_lectures"
        cached_data = cache.get(cache_key)

        if cached_data:
            return Response(cached_data, status=status.HTTP_200_OK)

        # 수강 중인 강의 목록 조회
        lectures = Lecture.objects.filter(course__enrollment__student=student, course__enrollment__is_active=True)
        if not lectures.exists():
            return Response({"redirect_url": "https://sorisangsang.umdoong.shop/classinfo/harmonics"}, status=302)

        response_data = []
        for lecture in lectures:
            total_videos = ChapterVideo.objects.filter(lecture_chapter__lecture=lecture).count()
            completed_videos = ProgressTracking.objects.filter(
                chapter_video__lecture_chapter__lecture=lecture, student=student, is_completed=True
            ).count()
            progress_rate = (completed_videos / total_videos) * 100 if total_videos > 0 else 0

            serialized_lecture = LectureListSerializer(lecture, context={"request": request}).data
            serialized_lecture["progress_rate"] = round(progress_rate, 2)
            response_data.append(serialized_lecture)

        # Redis에 캐싱 (1시간)
        cache.set(cache_key, response_data, timeout=3600)

        return Response(response_data, status=status.HTTP_200_OK)


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
            cache_key = f"lecture_chapters:{lecture_id}"
            cached_data = redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)

                # 캐싱된 데이터에서 download_url을 새로 생성
                for chapter in data:
                    material_info = chapter.get("material_info")
                    if material_info:
                        object_key = material_info["object_key"]
                        original_file_name = material_info["file_name"]

                        material_info["download_url"] = generate_material_signed_url(
                            object_key, original_filename=original_file_name
                        )

                return Response(data, status=status.HTTP_200_OK)

            # Redis에 데이터가 없으면 DB 조회
            chapters = LectureChapter.objects.filter(lecture_id=lecture_id)
            if not chapters.exists():
                return Response({"error": "해당 챕터를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            serializer = LectureChapterSerializer(chapters, many=True, context={"request": request})
            response_data = serializer.data

            # 캐싱할 때 download_url을 제외
            for chapter in response_data:
                if chapter.get("material_info"):
                    chapter["material_info"].pop("download_url", None)

            redis_client.setex(cache_key, 18000, json.dumps(response_data))

            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoProgressRetrieveView(APIView):
    """강의 영상 학습 진행률 조회 API (GET)"""

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 조회",
        description=(
            "** 특정 강의 영상(chapter_video)에 대한 학생의 학습 진행률을 조회합니다.**\n\n"
            "- `progress`: 영상 학습 진행률 (%)\n"
            "- `is_completed`: 영상 학습 완료 여부 (98% 이상이면 True)\n"
            "- `student_id`: 진행률을 조회하는 학생의 ID"
        ),
        responses={
            200: ProgressTrackingSerializer,
            403: OpenApiResponse(description="권한 없음 (로그인 필요)"),
            404: OpenApiResponse(description="진행 데이터를 찾을 수 없음"),
            500: OpenApiResponse(description="서버 내부 오류"),
        },
        tags=["Course"],
    )
    def get(self, request, chapter_video_id):
        try:
            student = Student.objects.get(user=request.user)
            progress_tracking = ProgressTracking.objects.get(student=student, chapter_video_id=chapter_video_id)

            return Response(ProgressTrackingSerializer(progress_tracking).data, status=status.HTTP_200_OK)

        except ProgressTracking.DoesNotExist:
            return Response(
                {"error": "이 강의 영상에 대한 학습 기록이 없습니다. 학습을 시작하세요."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Student.DoesNotExist:
            return Response({"error": "학생 정보가 등록되지 않았습니다."}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {"error": "서버 내부 오류", "details": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ChapterVideoProgressCreateView(APIView):
    """강의 영상 학습 진행률 생성 API (POST)"""

    permission_classes = [IsEnrolledStudent]

    @extend_schema(
        summary="강의 영상 학습 진행률 생성",
        description=(
            "** 강의 영상을 학습한 기록을 저장합니다.**\n\n"
            "- `last_watched_time` : 사용자가 마지막으로 시청한 시간 (초 단위)\n"
            "- `total_duration` : 전체 영상 길이 (초 단위, 프론트엔드 제공)\n"
            "- `progress`는 자동 계산되며, 999.99 이상이면 최대 99.99로 제한됩니다.\n"
            "- `is_completed`는 98% 이상이면 자동으로 `True` 처리됩니다.\n"
        ),
        request={
            "application/json": {
                "example": {
                    "last_watched_time": 120,  # 사용자가 마지막으로 본 위치 (초 단위)
                    "total_duration": 600,  # 영상 전체 길이 (초 단위, 프론트에서 제공해야 함)
                }
            }
        },
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
        description=(
            "특정 강의 영상(chapter_video)의 학습 진행률을 수정합니다.\n\n"
            "** 주의:**\n"
            "- `total_duration` 값은 **프론트엔드에서 제공 합니다.**\n"
            "- `total_duration`은 백엔드에서 저장되지 않으며, `progress` 및 `is_completed` 계산을 위해 사용됩니다."
        ),
        request={
            "application/json": {
                "example": {
                    "last_watched_time": 120,  # 사용자가 마지막으로 시청한 시간 (초 단위)
                    "total_duration": 600,  # 영상 전체 길이 (초 단위, 프론트엔드 제공)
                }
            }
        },
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
                "https://sorisangsang.umdoong.shop",
                "https://api.umdoong.shop",
                "http://127.0.0.1:8000",
                "http://127.0.0.1:3000",
                "http://localhost:3000",
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

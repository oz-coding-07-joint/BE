import os
import re

import boto3
from rest_framework import serializers

from apps.common.utils import generate_material_signed_url
from apps.courses.models import ChapterVideo, Lecture, LectureChapter, ProgressTracking
from apps.users.models import Instructor, Student
from config.settings import base


class LectureListSerializer(serializers.ModelSerializer):
    """과목 목록 조회 Serializer"""

    progress_rate = serializers.SerializerMethodField()  # 동적 필드

    class Meta:
        model = Lecture
        fields = ["id", "title", "thumbnail", "progress_rate"]

    def get_progress_rate(self, obj):
        """강의 진행률 계산: 완료된 강의 영상 수 / 전체 강의 영상 수 * 100"""
        total_videos = ChapterVideo.objects.filter(lecture_chapter__lecture=obj).count()
        completed_videos = ProgressTracking.objects.filter(
            chapter_video__lecture_chapter__lecture=obj, is_completed=True
        ).count()

        if total_videos == 0:
            return 0.0  # 강의 영상이 없으면 0%

        return round((completed_videos / total_videos) * 100, 2)  # 퍼센트 변환 (소수점 2자리)


class InstructorSerializer(serializers.ModelSerializer):
    """강사 정보 Serializer"""

    nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = Instructor
        fields = ["id", "nickname", "experience"]


class LectureDetailSerializer(serializers.ModelSerializer):
    """과목 상세 조회 Serializer"""

    instructor = InstructorSerializer()

    class Meta:
        model = Lecture
        fields = ["id", "title", "introduction", "learning_objective", "instructor"]


class ChapterVideoTitleSerializer(serializers.ModelSerializer):
    """챕터 내 강의 영상 제목 Serializer"""

    class Meta:
        model = ChapterVideo
        fields = ["id", "title"]


class LectureChapterSerializer(serializers.ModelSerializer):
    """챕터 목록 조회 Serializer (학습 자료 다운로드 URL 포함)"""

    chapter_video_titles = ChapterVideoTitleSerializer(many=True, source="chaptervideo_set")
    material_info = serializers.SerializerMethodField()  # material_url과 원래 파일명 반환
    chapter_video_titles = serializers.SerializerMethodField()
    material_info = serializers.SerializerMethodField()  # 학습 자료 다운로드 URL 포함

    class Meta:
        model = LectureChapter
        fields = ["id", "lecture_id", "title", "material_info", "chapter_video_titles"]

    def get_chapter_video_titles(self, obj):
        """챕터에 포함된 강의 영상 제목을 리스트로 반환"""
        return [{"id": v.id, "title": v.title} for v in obj.chaptervideo_set.all()]

    def get_material_info(self, obj):
        """학습 자료(material_url) 존재 시 Signed URL 반환"""
        if not obj.material_url:
            return None  # 학습 자료가 없는 경우 None 반환

        file_name = os.path.basename(obj.material_url.name)  # 원본 파일명 추출
        original_file_name = self.extract_original_filename(file_name)  # UUID 제거

        signed_url = generate_material_signed_url(
            object_key=obj.material_url.name,
            original_filename=original_file_name,  # 이게 다운로드 파일명으로 사용됨
        )

        return {
            "file_name": original_file_name,  # 사용자에게 보여줄 이름
            "object_key": obj.material_url.name,
            "download_url": signed_url,  # 서명된 S3 다운로드 URL
        }

    @staticmethod
    def extract_original_filename(file_name):
        """
        파일명에서 UUID 및 접두어(materials_) 제거하여 원래 파일명만 반환
        """
        pattern = r"^(?:materials_)?[\w-]+_([\w가-힣.-]+)$"

        match = re.match(pattern, file_name)
        if match:
            return match.group(1)  # UUID 제거 후 원래 파일명 반환
        return file_name  # 매칭 안 되면 기존 파일명 반환

    def generate_signed_url(self, obj):
        """
        Referrer를 검증하여 Signed URL을 반환
        """
        request = self.context.get("request")

        allowed_referrers = [
            "https://sorisangsang.umdoong.shop",
            "https://api.umdoong.shop",
            "http://127.0.0.1:8000",
            "http://127.0.0.1:3000",
            "http://localhost:3000",
        ]

        # Referrer 체크 (필수 요청이 아닌 경우 항상 새로운 URL 반환)
        if request:
            referrer = request.META.get("HTTP_REFERER", "")
            if referrer and not any(referrer.startswith(allowed) for allowed in allowed_referrers):
                print(f"잘못된 referrer: {referrer}")  # 디버깅용 출력
                return None  # Referrer가 허용되지 않으면 Signed URL 제공 안 함

        # 새로운 Signed URL 강제 생성
        return generate_material_signed_url(obj.material_url.name, expiration=300)


class ProgressTrackingSerializer(serializers.ModelSerializer):
    """강의 영상 학습 진행률 조회 Serializer"""

    student_id = serializers.PrimaryKeyRelatedField(source="student.id", read_only=True)
    progress = serializers.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        model = ProgressTracking
        fields = ["id", "student_id", "progress", "is_completed"]


class ProgressTrackingCreateSerializer(serializers.ModelSerializer):
    last_watched_time = serializers.FloatField()
    progress = serializers.FloatField(read_only=True)  # progress 추가

    class Meta:
        model = ProgressTracking
        fields = ["last_watched_time", "progress"]  # 불필요한 필드 제거

    def validate_last_watched_time(self, value):
        """last_watched_time이 음수값이 되는 것을 방지"""
        if value < 0:
            raise serializers.ValidationError("last_watched_time은 0보다 작을 수 없습니다.")
        return value

    def create(self, validated_data):
        """student와 chapter_video를 자동 설정"""
        request = self.context["request"]
        student = Student.objects.get(user=request.user)  #  현재 로그인한 사용자의 student 가져오기
        chapter_video_id = self.context["chapter_video_id"]
        chapter_video = ChapterVideo.objects.get(id=chapter_video_id)

        last_watched_time = validated_data["last_watched_time"]
        total_duration = request.data.get("total_duration", 1)  #  프론트엔드에서 제공하는 total_duration 사용

        #  진행률(progress) 계산 (음수 방지)
        progress = max((last_watched_time / total_duration) * 100, 0) if total_duration > 0 else 0
        is_completed = progress >= 98  #  98% 이상이면 완료 처리

        tracking = ProgressTracking.objects.create(
            student=student,
            chapter_video=chapter_video,
            last_watched_time=last_watched_time,
            progress=progress,
            is_completed=is_completed,
        )

        return tracking  #  생성된 객체 반환 (progress 값 포함)


class ProgressTrackingUpdateSerializer(serializers.ModelSerializer):
    last_watched_time = serializers.FloatField(help_text="사용자가 마지막으로 시청한 시간 (초 단위)")
    total_duration = serializers.FloatField(write_only=True, help_text="영상 전체 길이 (초 단위, 프론트엔드 제공)")

    class Meta:
        model = ProgressTracking
        fields = ["last_watched_time", "total_duration", "progress", "is_completed"]
        read_only_fields = ["progress", "is_completed"]  # progress와 is_completed는 자동 계산

    def validate(self, data):
        """last_watched_time이 음수값이 되거나 영상 길이를 초과하지 않도록 검증"""
        instance = self.instance
        last_watched_time = data.get("last_watched_time", instance.last_watched_time)
        total_duration = data.get("total_duration")

        if total_duration is None:
            raise serializers.ValidationError("total_duration 값이 필요합니다.")  # 필수 값 검증

        if last_watched_time < 0:
            raise serializers.ValidationError("last_watched_time은 0보다 작을 수 없습니다.")

        if last_watched_time > total_duration:
            raise serializers.ValidationError("last_watched_time이 영상 길이를 초과할 수 없습니다.")

        return data

    def update(self, instance, validated_data):
        """진행률 계산 시 프론트에서 제공한 total_duration 사용"""
        last_watched_time = validated_data.get("last_watched_time", instance.last_watched_time)
        total_duration = validated_data.get("total_duration")

        progress = (last_watched_time / total_duration) * 100 if total_duration > 0 else 0
        is_completed = progress >= 98  # 98% 이상이면 완료 처리

        instance.last_watched_time = last_watched_time
        instance.progress = progress
        instance.is_completed = is_completed
        instance.save()

        return instance


class ChapterVideoSerializer(serializers.ModelSerializer):
    video_url = serializers.SerializerMethodField()

    class Meta:
        model = ChapterVideo
        fields = ["id", "title", "video_url"]

    def get_video_url(self, obj):
        """Signed URL을 반환하여 인증된 사용자만 접근 가능하게 변경"""
        if not obj.video_url:
            return None

        s3_client = boto3.client(
            "s3",
            endpoint_url=base.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=base.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=base.AWS_SECRET_ACCESS_KEY,
            region_name=base.AWS_S3_REGION_NAME,
        )

        bucket_name = base.AWS_STORAGE_BUCKET_NAME
        object_key = obj.video_url.name

        # Signed URL 생성 (30분 유효)
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=60 * 30,  # 30분 후 만료
            HttpMethod="GET",
        )
        return url

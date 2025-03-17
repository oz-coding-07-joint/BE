import os
import re

from rest_framework import serializers

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
    """챕터 목록 조회 Serializer (챕터 내 강의 영상 제목 포함)"""

    chapter_video_titles = ChapterVideoTitleSerializer(many=True, source="chaptervideo_set")
    material_info = serializers.SerializerMethodField()  # material_url과 원래 파일명 반환

    class Meta:
        model = LectureChapter
        fields = ["id", "lecture_id", "title", "material_info", "chapter_video_titles"]

    def get_material_info(self, obj):
        """material_url과 원래 파일명을 반환"""
        if obj.material_url:
            file_name = os.path.basename(obj.material_url.name)  # 전체 파일명 추출
            original_file_name = self.extract_original_filename(file_name)  # UUID 및 접두어 제거

            return {"url": obj.material_url.url, "file_name": original_file_name}
        return None  # 자료가 없는 경우 None 반환

    def extract_original_filename(self, file_name):
        """
        파일명에서 UUID와 접두어(materials_)를 제거하여 원래 파일명만 추출하는 함수
        예:
        - "materials_9dbfa93c-9936-4d48-8732-54dbb25961c6_공주.png" → "공주.png"
        - "videos_5d6f8e0b-7843-4e47-b4f7-828b7f56a0d2_강의.mp4" → "강의.mp4"
        """
        # UUID 패턴: _(UUID)_ (언더스코어 포함)
        pattern = r"^(materials|videos|thumbnails)?_\w{8}-\w{4}-\w{4}-\w{4}-\w{12}_"

        # 정규식으로 UUID + 접두어 제거
        return re.sub(pattern, "", file_name)


class ProgressTrackingSerializer(serializers.ModelSerializer):
    """강의 영상 학습 진행률 조회 Serializer"""

    student_id = serializers.PrimaryKeyRelatedField(source="student.id", read_only=True)

    class Meta:
        model = ProgressTracking
        fields = ["id", "student_id", "progress", "is_completed"]


class ProgressTrackingCreateSerializer(serializers.ModelSerializer):
    last_watched_time = serializers.FloatField()
    progress = serializers.FloatField(read_only=True)  # ✅ progress 추가

    class Meta:
        model = ProgressTracking
        fields = ["last_watched_time", "progress"]  # ✅ 불필요한 필드 제거

    def validate_last_watched_time(self, value):
        """✅ last_watched_time이 음수값이 되는 것을 방지"""
        if value < 0:
            raise serializers.ValidationError("last_watched_time은 0보다 작을 수 없습니다.")
        return value

    def create(self, validated_data):
        """✅ student와 chapter_video를 자동 설정"""
        request = self.context["request"]
        student = Student.objects.get(user=request.user)  # ✅ 현재 로그인한 사용자의 student 가져오기
        chapter_video_id = self.context["chapter_video_id"]
        chapter_video = ChapterVideo.objects.get(id=chapter_video_id)

        last_watched_time = validated_data["last_watched_time"]
        total_duration = request.data.get("total_duration", 1)  # ✅ 프론트엔드에서 제공하는 total_duration 사용

        # ✅ 진행률(progress) 계산 (음수 방지)
        progress = max((last_watched_time / total_duration) * 100, 0) if total_duration > 0 else 0
        is_completed = progress >= 98  # ✅ 98% 이상이면 완료 처리

        tracking = ProgressTracking.objects.create(
            student=student,
            chapter_video=chapter_video,
            last_watched_time=last_watched_time,
            progress=progress,
            is_completed=is_completed,
        )

        return tracking  # ✅ 생성된 객체 반환 (progress 값 포함)


class ProgressTrackingUpdateSerializer(serializers.ModelSerializer):
    last_watched_time = serializers.FloatField()

    class Meta:
        model = ProgressTracking
        fields = ["last_watched_time", "progress", "is_completed"]
        read_only_fields = ["progress", "is_completed"]

    def validate(self, data):
        """✅ last_watched_time이 음수값이 되거나 영상 길이를 초과하지 않도록 검증"""
        instance = self.instance
        last_watched_time = data.get("last_watched_time", instance.last_watched_time)
        total_duration = self.context["request"].data.get("total_duration")  # ✅ 프론트에서 제공

        if total_duration is None:
            raise serializers.ValidationError("total_duration 값이 필요합니다.")  # ✅ 필수 값 검증

        if last_watched_time < 0:
            raise serializers.ValidationError("last_watched_time은 0보다 작을 수 없습니다.")

        if last_watched_time > total_duration:
            raise serializers.ValidationError("last_watched_time이 영상 길이를 초과할 수 없습니다.")

        return data

    def update(self, instance, validated_data):
        """✅ 진행률 계산 시 프론트에서 제공한 total_duration 사용"""
        last_watched_time = validated_data.get("last_watched_time", instance.last_watched_time)
        total_duration = self.context["request"].data.get("total_duration")

        progress = (last_watched_time / total_duration) * 100 if total_duration > 0 else 0
        is_completed = progress >= 98  # ✅ 98% 이상이면 완료 처리

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
        """NCP Object Storage에서 직접 접근 가능한 URL 반환"""
        if obj.video_url:  # video_url 필드가 이미 존재하는 경우 직접 반환
            return obj.video_url

        if obj.video_file:  # video_file이 존재하면 S3 URL을 생성
            return f"https://{base.AWS_STORAGE_BUCKET_NAME}.kr.object.ncloudstorage.com/{obj.video_file.name}"

        return None

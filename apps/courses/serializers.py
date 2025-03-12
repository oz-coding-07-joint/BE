from rest_framework import serializers

from apps.courses.models import ChapterVideo, Lecture, LectureChapter, ProgressTracking
from apps.users.models import Instructor, Student, User


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

    class Meta:
        model = LectureChapter
        fields = ["id", "lecture_id", "title", "material_url", "chapter_video_titles"]


class ProgressTrackingCreateSerializer(serializers.ModelSerializer):
    """강의 영상 학습 진행률 생성 Serializer"""

    class Meta:
        model = ProgressTracking
        fields = ["chapter_video", "progress", "last_watched_time"]

    def create(self, validated_data):
        """
        - 처음 학습할 경우 진행률 데이터를 생성한다.
        - 기본 progress는 0.0, is_completed는 False로 설정된다.
        """
        validated_data.setdefault("progress", 0.0)
        validated_data.setdefault("is_completed", False)

        return super().create(validated_data)


class ProgressTrackingSerializer(serializers.ModelSerializer):
    """강의 영상 학습 진행률 조회 Serializer"""

    student_id = serializers.PrimaryKeyRelatedField(source="student.id", read_only=True)

    class Meta:
        model = ProgressTracking
        fields = ["id", "student_id", "progress", "is_completed"]


class ProgressTrackingUpdateSerializer(serializers.ModelSerializer):
    """강의 영상 학습 진행률 업데이트 Serializer"""

    class Meta:
        model = ProgressTracking
        fields = ["progress", "last_watched_time"]

    def update(self, instance, validated_data):
        """
        - `progress` 값이 100%에 도달하면 `is_completed=True` 자동 설정
        - `last_watched_time`도 업데이트 가능
        """
        instance.progress = validated_data.get("progress", instance.progress)
        instance.last_watched_time = validated_data.get("last_watched_time", instance.last_watched_time)

        if instance.progress >= 100.0:
            instance.progress = 100.0  # 최대 100% 유지
            instance.is_completed = True  # 완료 처리

        instance.save()
        return instance


class ChapterVideoSerializer(serializers.ModelSerializer):
    """강의 영상 상세 조회 Serializer"""

    class Meta:
        model = ChapterVideo
        fields = ["id", "video_url"]

from rest_framework import serializers

from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    """수강 신청 직렬화 클래스.

    Enrollment 모델의 모든 필드를 직렬화.

    Attributes:
        course: 강의 정보.
        student: 수강 신청한 학생.
        is_active: 신청 승인 여부.
    """

    class Meta:
        model = Enrollment
        fields = ["id", "course", "student", "is_active"]


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """수강 중인 수업 조회를 위한 직렬화 클래스.

    Course의 title 정보를 추가로 포함하여 직렬화.

    Attributes:
        title: 연결된 강의의 제목 (읽기 전용).
    """

    title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "course", "title", "is_active"]

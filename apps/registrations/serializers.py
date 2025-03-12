from rest_framework import serializers

from .models import Enrollment


# 수강 신청
class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ["id", "course", "student", "is_active"]


# 수강중인 수업 조회
class EnrollmentDetailSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Enrollment
        fields = ["id", "course", "title", "is_active"]

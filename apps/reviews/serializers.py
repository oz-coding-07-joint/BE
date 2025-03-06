from rest_framework import serializers

from .models import Review


# 후기 등록 및 수업 후기 조회
class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["id", "lecture", "student", "student_nickname", "star", "content"]


# 내가 작성한 후기 조회
class ReviewDetailSerializer(serializers.ModelSerializer):
    # Lecture의 title도 함께 반환 (Lecture 모델에 title 필드가 있다고 가정)
    lecture_title = serializers.CharField(source="lecture.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "lecture", "lecture_title", "star", "content"]

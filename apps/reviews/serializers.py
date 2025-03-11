from rest_framework import serializers

from .models import Review


# 수업 후기 전체 조회
class ReviewSerializer(serializers.ModelSerializer):
    lecture_title = serializers.CharField(source="lecture.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "lecture", "student", "lecture_title", "student_nickname", "star", "content"]


# 후기 등록
class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ["star", "content"]  # 클라이언트는 star와 content만 전송

    def create(self, validated_data):
        # 뷰에서 context로 전달받은 lecture, student를 사용
        lecture = self.context.get("lecture")
        student = self.context.get("student")
        if lecture is None or student is None:
            raise serializers.ValidationError("Lecture와 Student 정보가 필요합니다.")
        validated_data["lecture"] = lecture
        validated_data["student"] = student
        # 예를 들어 student.user.nickname으로 닉네임 설정 (필요에 따라 수정)
        validated_data["student_nickname"] = student.user.nickname
        return super().create(validated_data)


# 내가 작성한 후기 조회
class ReviewDetailSerializer(serializers.ModelSerializer):
    # Lecture의 title도 함께 반환 (Lecture 모델에 title 필드가 있다고 가정)
    lecture_title = serializers.CharField(source="lecture.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "lecture", "lecture_title", "student_nickname", "star", "content"]

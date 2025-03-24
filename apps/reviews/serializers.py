from rest_framework import serializers

from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """수업 후기 전체 조회를 위한 직렬화 클래스.

    Lecture의 제목 정보를 추가로 포함하여 직렬화.

    Attributes:
        lecture_title: 강의 제목 (읽기 전용).
    """

    lecture_title = serializers.CharField(source="lecture.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "lecture", "student", "lecture_title", "student_nickname", "star", "content"]


class ReviewCreateSerializer(serializers.ModelSerializer):
    """후기 등록을 위한 직렬화 클래스.

    클라이언트는 star와 content만 전송하며
    나머지 정보는 뷰에서 context를 통해 제공받음.
    """

    class Meta:
        model = Review
        fields = ["star", "content"]  # 클라이언트는 star와 content만 전송

    def create(self, validated_data):
        """새로운 후기 객체를 생성.

        Context에서 전달받은 lecture와 student 정보를 사용하며
        student의 닉네임을 student_nickname에 할당.

        Args:
            validated_data (dict): 클라이언트에서 전달받은 데이터.

        Returns:
            Review: 생성된 후기 인스턴스.

        Raises:
            serializers.ValidationError: lecture나 student 정보가 context에 없을 경우.
        """
        lecture = self.context.get("lecture")
        student = self.context.get("student")
        if lecture is None or student is None:
            raise serializers.ValidationError("Lecture와 Student 정보가 필요합니다.")
        validated_data["lecture"] = lecture
        validated_data["student"] = student
        validated_data["student_nickname"] = student.user.nickname
        return super().create(validated_data)


class ReviewDetailSerializer(serializers.ModelSerializer):
    """내가 작성한 후기를 조회하기 위한 직렬화 클래스.

    Lecture의 제목도 함께 반환.

    Attributes:
        lecture_title: 강의 제목 (읽기 전용).
    """

    lecture_title = serializers.CharField(source="lecture.title", read_only=True)

    class Meta:
        model = Review
        fields = ["id", "lecture", "lecture_title", "student_nickname", "star", "content"]

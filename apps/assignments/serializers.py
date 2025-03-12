from rest_framework import serializers

from .models import Assignment, AssignmentComment


# 강의 챕터별로 과제 목록을 조회
class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "chapter_video", "title", "content", "file_url"]


# 수강생 과제 및 피드백 목록 조회
class AssignmentCommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = AssignmentComment
        fields = ["id", "user", "nickname", "assignment", "parent", "file_url", "content", "created_at", "replies"]

    def get_replies(self, obj):
        qs = obj.replies.all()
        return AssignmentCommentSerializer(qs, many=True).data


# 강의 과제 제출
class AssignmentCommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentComment
        fields = ["content", "file_url", "parent"]

    def create(self, validated_data):
        assignment = self.context.get("assignment")
        user = self.context.get("user")
        if assignment is None or user is None:
            raise serializers.ValidationError("Assignment와 User 정보가 필요합니다.")
        validated_data["assignment"] = assignment
        validated_data["user"] = user
        return super().create(validated_data)

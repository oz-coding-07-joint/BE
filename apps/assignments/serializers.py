from rest_framework import serializers

from .models import Assignment, AssignmentComment


# 강의 챕터별로 과제 목록을 조회
class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ["id", "chapter_video", "title", "content", "file_url"]


# 강의 과제 제출, 수강생 과제 및 피드백 목록 조회
class AssignmentCommentSerializer(serializers.ModelSerializer):
    replies = serializers.SerializerMethodField()
    nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = AssignmentComment
        fields = ["id", "user", "nickname", "assignment", "parent", "file_url", "content", "created_at", "replies"]

    def get_replies(self, obj):
        qs = obj.replies.all()
        return AssignmentCommentSerializer(qs, many=True).data

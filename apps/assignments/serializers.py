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

    class Meta:
        model = AssignmentComment
        fields = ["id", "user", "parent", "file_url", "content", "replies"]

    def get_replies(self, obj):
        qs = obj.replies.all()
        return AssignmentCommentSerializer(qs, many=True).data

from rest_framework import serializers

from .models import Assignment, AssignmentComment


class AssignmentSerializer(serializers.ModelSerializer):
    """강의 챕터별 과제 목록 조회를 위한 직렬화 클래스.

    Attributes:
        chapter_video: 연결된 ChapterVideo 인스턴스.
        title: 과제 제목.
        content: 과제 내용.
        file_url: 과제 첨부 파일 URL.
    """

    class Meta:
        model = Assignment
        fields = ["id", "chapter_video", "title", "content", "file_url"]


class AssignmentCommentSerializer(serializers.ModelSerializer):
    """수강생 과제 및 피드백 목록 조회를 위한 직렬화 클래스.

    Attributes:
        replies: 해당 댓글에 대한 대댓글들을 재귀적으로 직렬화.
        nickname: 작성자의 닉네임(읽기 전용).
    """

    replies = serializers.SerializerMethodField()
    nickname = serializers.CharField(source="user.nickname", read_only=True)

    class Meta:
        model = AssignmentComment
        fields = ["id", "user", "nickname", "assignment", "parent", "file_url", "content", "created_at", "replies"]

    def get_replies(self, obj):
        """대댓글(replies)을 직렬화하여 반환.

        Args:
            obj (AssignmentComment): 댓글 인스턴스.

        Returns:
            list: 직렬화된 대댓글 목록.
        """
        qs = obj.replies.all()
        return AssignmentCommentSerializer(qs, many=True).data


class AssignmentCommentCreateSerializer(serializers.ModelSerializer):
    """강의 과제 제출을 위한 직렬화 클래스.

    클라이언트는 'content', 'file_url', 'parent'만 전송하며
    assignment와 request.user 정보는 context를 통해 전달받음.
    """

    class Meta:
        model = AssignmentComment
        fields = ["content", "file_url", "parent"]

    def create(self, validated_data):
        """새로운 과제 댓글 객체를 생성.

        Context에서 전달받은 assignment와 user 정보를 사용하여 객체를 생성.

        Args:
            validated_data (dict): 클라이언트에서 전달받은 데이터.

        Returns:
            AssignmentComment: 생성된 과제 댓글 인스턴스.

        Raises:
            serializers.ValidationError: assignment나 user 정보가 context에 없을 경우.
        """
        assignment = self.context.get("assignment")
        user = self.context.get("user")
        if assignment is None or user is None:
            raise serializers.ValidationError("Assignment와 User 정보가 필요합니다.")
        validated_data["assignment"] = assignment
        validated_data["user"] = user
        return super().create(validated_data)

import os
import re

import boto3
from rest_framework import serializers

from apps.common.utils import generate_download_signed_url

from .models import Assignment, AssignmentComment


class AssignmentSerializer(serializers.ModelSerializer):
    """강의 과제 목록 조회를 위한 직렬화 클래스.

    Assignment 인스턴스의 기본 정보와 함께 파일이 존재할 경우
    다운로드에 필요한 정보를 제공하는 download_info 필드를 포함.

    Attributes:
        chapter_video (ChapterVideo): 연결된 ChapterVideo 인스턴스.
        title (str): 과제 제목.
        content (str): 과제 내용.
        file_url (FileField): 과제 첨부 파일 URL.
        download_info (dict or None): 파일이 존재할 경우 다운로드 정보를 담은 딕셔너리.
            - file_name (str): UUID 및 구분자가 제거된 원래 파일명.
            - object_key (str): 실제 파일 저장 경로.
            - download_url (str): 서명된 다운로드 URL.
    """

    download_info = serializers.SerializerMethodField()

    class Meta:
        model = Assignment
        fields = ["id", "chapter_video", "title", "content", "file_url", "download_info"]

    def get_download_info(self, obj):
        """파일이 존재하면 다운로드 정보를 담은 딕셔너리를 반환.

                Args:
                    obj (Assignment): 직렬화할 Assignment 인스턴스.

                Returns:
                    dict or None: 파일이 존재할 경우 다운로드 정보 딕셔너리 없으면 None.
                """
        if obj.file_url:
            original_file_name = os.path.basename(obj.file_url.name)
            processed_filename = self.extract_original_filename(original_file_name)
            signed_url = generate_download_signed_url(
                object_key=obj.file_url.name,
                original_filename=processed_filename,
            )
            return {
                "file_name": processed_filename,
                "object_key": obj.file_url.name,
                "download_url": signed_url,
            }
        return None

    @staticmethod
    def extract_original_filename(file_name):
        """UUID 및 구분자(_)를 제거하여 원래 파일명만 반환.

        Args:
            file_name (str): 원본 파일명.

        Returns:
            str: UUID와 구분자가 제거된 파일명.
        """
        name, ext = os.path.splitext(file_name)
        pattern = r"^(?:materials_)?(.*)_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
        match = re.match(pattern, name)
        if match:
            return f"{match.group(1)}{ext}"
        return file_name


class AssignmentCommentSerializer(serializers.ModelSerializer):
    """수강생 과제 및 피드백 목록 조회를 위한 직렬화 클래스.

    댓글의 기본 정보와 함께 대댓글(replies) 및 파일 다운로드 정보(download_info)를 제공.

    Attributes:
        replies (list): 해당 댓글에 대한 대댓글들을 재귀적으로 직렬화한 목록.
        nickname (str): 작성자의 닉네임 (읽기 전용).
        download_info (dict or None): 첨부 파일이 있을 경우 다운로드 정보를 담은 딕셔너리.
            - file_name (str): UUID 및 구분자가 제거된 원래 파일명.
            - object_key (str): 실제 파일 저장 경로.
            - download_url (str): 서명된 다운로드 URL.
    """

    replies = serializers.SerializerMethodField()
    nickname = serializers.CharField(source="user.nickname", read_only=True)
    download_info = serializers.SerializerMethodField()

    class Meta:
        model = AssignmentComment
        fields = [
            "id",
            "user",
            "nickname",
            "assignment",
            "parent",
            "file_url",
            "content",
            "created_at",
            "replies",
            "download_info",
        ]

    def get_replies(self, obj):
        """대댓글(replies)을 직렬화하여 반환.

        Args:
            obj (AssignmentComment): 댓글 인스턴스.

        Returns:
            list: 직렬화된 대댓글 목록.
        """
        qs = obj.replies.all()
        return AssignmentCommentSerializer(qs, many=True).data

    def get_download_info(self, obj):
        """첨부 파일이 있을 경우, 다운로드 정보를 담은 딕셔너리를 반환.

         Args:
             obj (AssignmentComment): 직렬화할 댓글 인스턴스.

         Returns:
             dict or None: 파일이 있을 경우 다운로드 정보 딕셔너리 없으면 None.
         """
        if obj.file_url:
            original_file_name = os.path.basename(obj.file_url.name)
            processed_filename = self.extract_original_filename(original_file_name)
            signed_url = generate_download_signed_url(
                object_key=obj.file_url.name, original_filename=processed_filename, expiration=3600
            )
            return {
                "file_name": processed_filename,
                "object_key": obj.file_url.name,
                "download_url": signed_url,
            }
        return None

    @staticmethod
    def extract_original_filename(file_name):
        """UUID 및 구분자(_)를 제거하여 원래 파일명만 반환.

        Args:
            file_name (str): 원본 파일명.

        Returns:
            str: UUID 및 구분자가 제거된 파일명.
        """
        name, ext = os.path.splitext(file_name)
        pattern = r"^(?:assignments_)?(.*)_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$"
        match = re.match(pattern, name)
        if match:
            return f"{match.group(1)}{ext}"
        return file_name


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

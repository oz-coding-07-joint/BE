from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import (
    assignment_comment_file_path,
    assignment_material_path,
    delete_file_from_ncp,
)
from apps.courses.models import ChapterVideo
from apps.users.models import User


class Assignment(BaseModel):
    """강의 과제 모델.

    강의의 특정 ChapterVideo에 연결된 과제 정보를 저장하며
    파일이 변경되거나 삭제될 때 NCP Object Storage에서 파일 삭제를 처리.
    """

    chapter_video = models.ForeignKey(ChapterVideo, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.CharField(max_length=1000)
    file_url = models.FileField(upload_to=assignment_material_path, null=True, blank=True)

    def save(self, *args, **kwargs):
        """과제 인스턴스를 저장.

        기존 인스턴스인 경우 파일이 변경되었으면 이전 파일을 삭제하며
        새 인스턴스에서 파일이 업로드되면 pk값을 생성하기 위해 두 번 저장.

        Args:
            *args: 부모 클래스의 save 메서드에 전달될 위치 인자.
            **kwargs: 부모 클래스의 save 메서드에 전달될 키워드 인자.
        """

        if self.pk:
            try:
                old_instance = Assignment.objects.get(pk=self.pk)
                # 파일이 존재하고 새 파일이 기존 파일과 다르면 기존 파일 삭제
                if old_instance.file_url and old_instance.file_url != self.file_url:
                    delete_file_from_ncp(old_instance.file_url.name)
            except Assignment.DoesNotExist:
                pass

        if not self.pk and self.file_url:
            temp_file = self.file_url
            self.file_url = None
            super().save(*args, **kwargs)
            self.file_url = temp_file
            super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """과제 인스턴스를 삭제.

        NCP Object Storage에서도 파일을 삭제.

        Args:
            *args: 부모 클래스의 delete 메서드에 전달될 위치 인자.
            **kwargs: 부모 클래스의 delete 메서드에 전달될 키워드 인자.
        """
        if self.file_url:
            delete_file_from_ncp(self.file_url.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        """과제 제목을 문자열로 반환.

        Returns:
            str: 과제의 제목.
        """
        return self.title

    class Meta:
        db_table = "assignment"


class AssignmentComment(BaseModel):
    """과제 댓글 모델.

    과제에 대한 학생의 제출 및 강사의 피드백을 저장하며
    파일이 첨부된 경우 NCP Object Storage에서 삭제를 처리.
    """

    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    file_url = models.FileField(upload_to=assignment_comment_file_path, null=True, blank=True)
    content = models.CharField(max_length=500)

    def delete(self, *args, **kwargs):
        """과제 댓글 인스턴스를 삭제.

        NCP Object Storage에서도 파일을 삭제.

        Args:
            *args: 부모 클래스의 delete 메서드에 전달될 위치 인자.
            **kwargs: 부모 클래스의 delete 메서드에 전달될 키워드 인자.
        """
        if self.file_url:
            delete_file_from_ncp(self.file_url.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        """댓글 작성자의 닉네임 또는 username을 문자열로 반환.

        Returns:
            str: 유저의 닉네임(존재할 경우) 또는 username.
        """
        return self.user.nickname if getattr(self.user, "nickname", None) else self.user.username

    class Meta:
        db_table = "assignment_comment"

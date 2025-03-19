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
    chapter_video = models.ForeignKey(ChapterVideo, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.CharField(max_length=1000)
    file_url = models.FileField(upload_to=assignment_material_path, null=True, blank=True)

    def save(self, *args, **kwargs):
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
        # NCP Object Storage에서도 파일 삭제
        if self.file_url:
            delete_file_from_ncp(self.file_url.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.title

    class Meta:
        db_table = "assignment"


class AssignmentComment(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    file_url = models.FileField(upload_to=assignment_comment_file_path, null=True, blank=True)
    content = models.CharField(max_length=500)

    def delete(self, *args, **kwargs):
        # NCP Object Storage에서도 파일 삭제
        if self.file_url:
            delete_file_from_ncp(self.file_url.name)
        super().delete(*args, **kwargs)

    def __str__(self):
        # 유저의 닉네임이 있으면 닉네임, 없으면 username 반환
        return self.user.nickname if getattr(self.user, "nickname", None) else self.user.username

    class Meta:
        db_table = "assignment_comment"

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import assignment_comment_file_path, assignment_material_path
from apps.courses.models import ChapterVideo
from apps.users.models import User


class Assignment(BaseModel):
    chapter_video = models.ForeignKey(ChapterVideo, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.CharField(max_length=1000)
    file_url = models.FileField(upload_to=assignment_material_path, null=True, blank=True)

    class Meta:
        db_table = "assignment"


class AssignmentComment(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent_id = models.ForeignKey("self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies")
    title = models.CharField(max_length=50)
    file_url = models.FileField(upload_to=assignment_comment_file_path, null=True, blank=True)
    content = models.CharField(max_length=500)

    class Meta:
        db_table = "assignment_comment"

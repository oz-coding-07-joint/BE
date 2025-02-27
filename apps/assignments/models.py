from django.db import models

from apps.common.models import BaseModel
from apps.courses.models import CourseMaterial
from apps.users.models import User


class Assignment(BaseModel):
    course_material = models.ForeignKey(CourseMaterial, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.CharField(max_length=1000)
    file_url = models.CharField(max_length=255)

    class Meta:
        db_table = "assignment"


class AssignmentInteraction(BaseModel):
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    parent_id = models.BigIntegerField()
    title = models.CharField(max_length=50)
    file_url = models.CharField(max_length=255)
    content = models.CharField(max_length=500)
    status = models.BooleanField(default=True)

    class Meta:
        db_table = "homework"

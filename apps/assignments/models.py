from django.db import models

from apps.common.models import BaseModel
from apps.courses.models import Lecture
from apps.users.models import Student


class Task(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.TextField()

    class Meta:
        db_table = "task"


class Homework(BaseModel):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    file_url = models.CharField(max_length=255)
    content = models.TextField()
    status = models.BooleanField(default=True)

    class Meta:
        db_table = "homework"


class HomeworkFeedback(BaseModel):
    homework = models.ForeignKey(Homework, related_name="homework_feedback", on_delete=models.CASCADE)
    instructor = models.ForeignKey(Student, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    content = models.TextField()

    class Meta:
        db_table = "homework_feedback"
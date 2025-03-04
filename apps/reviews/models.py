from django.db import models

from apps.common.models import BaseModel
from apps.courses.models import Lecture
from apps.users.models import User

class Review(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    student_nickname = models.CharField(max_length=20)
    star = models.DecimalField(max_digits=5, decimal_places=1)
    content = models.CharField(max_length=200)

    class Meta:
        db_table = "review"
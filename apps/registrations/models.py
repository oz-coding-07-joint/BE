from django.db import models

from apps.common.models import BaseModel
from apps.courses.models import Course
from apps.users.models import User


class Enrollment(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "enrollment"
from django.db import models

from apps.common.models import BaseModel
from apps.courses.models import Course
from apps.users.models import Student


class Enrollment(BaseModel):
    """수강 신청 모델.

    학생이 특정 강의를 신청한 정보를 저장.
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "enrollment"

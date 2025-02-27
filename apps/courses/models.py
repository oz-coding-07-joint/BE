from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User


class Course(BaseModel):
    subject = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_duration = models.SmallIntegerField(default=0)
    max_students = models.SmallIntegerField(default=0)

    class Meta:
        db_table = "class"


class Lecture(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    introduction = models.TextField()

    class Meta:
        db_table = "lecture"


class LectureCourse(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    material_url = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)

    class Meta:
        db_table = "lecture_course"


class CourseMaterial(BaseModel):
    lecture_course = models.ForeignKey(LectureCourse, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    lecture_video_url = models.CharField(max_length=255)

    class Meta:
        db_table = "course_material"


class Enrollment(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=False)

    class Meta:
        db_table = "enrollment"


class Review(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    student_nickname = models.CharField(max_length=20)
    star = models.DecimalField(max_digits=5, decimal_places=1)
    content = models.CharField(max_length=200)

    class Meta:
        db_table = "review"

from django.db import models

from apps.common.models import BaseModel
from apps.users.models import User


class Course(BaseModel):
    subject = models.CharField(max_length=50)  # 과정명
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 수강료
    total_duration = models.SmallIntegerField(default=0)  # 수강기간
    max_students = models.SmallIntegerField(default=0)  # 최대 수강생 수

    class Meta:
        db_table = "class"


class Lecture(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    introduction = models.CharField(max_length=1000)  # 강의 소개
    learning_objective = models.CharField(max_length=255)  # 학습 목표

    class Meta:
        db_table = "lecture"


class LectureCourse(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    material_url = models.CharField(max_length=255)  # 학습 자료

    class Meta:
        db_table = "lecture_course"


class CourseMaterial(BaseModel):
    lecture_course = models.ForeignKey(LectureCourse, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    lecture_video_url = models.CharField(max_length=255)  # 강의 영상

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

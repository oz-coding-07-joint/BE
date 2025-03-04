from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import class_lecture_file_path
from apps.users.models import Student, User


class Course(BaseModel):
    title = models.CharField(max_length=50)  # 과정명
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 수강료
    total_duration = models.SmallIntegerField(default=0)  # 수강기간
    max_students = models.SmallIntegerField(default=0)  # 최대 수강생 수

    class Meta:
        db_table = "class"


class Lecture(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=50)
    thumbnail = models.ImageField(upload_to=class_lecture_file_path, null=True, blank=True)
    introduction = models.CharField(max_length=1000)  # 강의 소개
    learning_objective = models.CharField(max_length=255)  # 학습 목표
    progress_rate = models.DecimalField(max_digits=5, decimal_places=2)  # 강의 진행 상황

    class Meta:
        db_table = "lecture"


class LectureChapter(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    material_url = models.FileField(upload_to=class_lecture_file_path, null=True, blank=True)  # 학습 자료

    class Meta:
        db_table = "lecture_chapter"


class ChapterVideo(BaseModel):
    lecture_chapter = models.ForeignKey(LectureChapter, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    video_url = models.FileField(upload_to=class_lecture_file_path, null=True, blank=True)  # 강의 영상

    class Meta:
        db_table = "chapter_video"


class ProgressTracking(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True)
    chapter_video = models.ForeignKey(ChapterVideo, on_delete=models.CASCADE)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_completed = models.BooleanField(default=False)  # 강의 완료 여부

    class Meta:
        db_table = "progress_tracking"
        unique_together = ("student", "chapter_video")

from django.db import models

from apps.common.models import BaseModel
from apps.common.utils import (
    class_lecture_file_path,
    delete_file_from_ncp,
    generate_ncp_signed_url,
)
from apps.users.models import Instructor, Student


class Course(BaseModel):
    title = models.CharField(max_length=50)  # 과정명
    price = models.DecimalField(max_digits=10, decimal_places=2)  # 수강료
    total_duration = models.SmallIntegerField(default=0)  # 수강기간
    max_students = models.SmallIntegerField(default=0)  # 최대 수강생 수

    def __str__(self):
        return self.title  # 과정명을 출력

    class Meta:
        db_table = "class"


class Lecture(BaseModel):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    instructor = models.ForeignKey(Instructor, on_delete=models.SET_NULL, null=True)
    title = models.CharField(max_length=50)
    thumbnail = models.ImageField(upload_to=class_lecture_file_path, null=True, blank=True)
    introduction = models.CharField(max_length=1000)  # 강의 소개
    learning_objective = models.CharField(max_length=255)  # 학습 목표
    progress_rate = models.DecimalField(max_digits=5, decimal_places=2)  # 강의 진행 상황

    def __str__(self):
        return f"{self.course.title} - {self.title}"  # 과정명 + 강의명을 출력

    def save(self, *args, **kwargs):
        """썸네일 변경 시 기존 썸네일 삭제"""
        if self.pk:
            old_instance = Lecture.objects.get(pk=self.pk)
            if old_instance.thumbnail and old_instance.thumbnail != self.thumbnail:
                delete_file_from_ncp(old_instance.thumbnail.name)  # 기존 파일 삭제

        super().save(*args, **kwargs)  # 새로운 파일 저장

    def delete(self, *args, **kwargs):
        """NCP Object Storage에서도 파일 삭제"""
        if self.thumbnail:
            delete_file_from_ncp(self.thumbnail.name)  # 파일 삭제 실행
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "lecture"


class LectureChapter(BaseModel):
    lecture = models.ForeignKey(Lecture, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    material_url = models.FileField(upload_to=class_lecture_file_path, null=True, blank=True)  # 학습 자료

    def __str__(self):
        return f"{self.lecture.title} - {self.title}"  # Lecture 제목 + 챕터 제목 출력

    def save(self, *args, **kwargs):
        """파일이 변경될 경우 기존 파일 삭제 후 새로운 파일 저장"""
        if self.pk:  # 기존 객체가 존재하는 경우
            old_instance = LectureChapter.objects.get(pk=self.pk)
            if old_instance.material_url and old_instance.material_url != self.material_url:
                delete_file_from_ncp(old_instance.material_url.name)  # 기존 파일 삭제

        super().save(*args, **kwargs)  # 새로운 파일 저장

    def delete(self, *args, **kwargs):
        """NCP Object Storage에서도 파일 삭제"""
        if self.material_url:
            delete_file_from_ncp(self.material_url.name)
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "lecture_chapter"


class ChapterVideo(BaseModel):
    lecture_chapter = models.ForeignKey(LectureChapter, on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    video_url = models.FileField(upload_to=class_lecture_file_path, null=True, blank=True)  # 강의 영상

    def get_video_url(self, user_id=None):
        """
        강의 영상의 Signed URL을 반환
        :param user_id: 현재 요청한 사용자 ID (보안 강화를 위해 추가)
        :return: Signed URL 또는 None
        """
        if self.video_url:
            return generate_ncp_signed_url(self.video_url.name, user_id=user_id)
        return None

    def save(self, *args, **kwargs):
        """강의 영상 변경 시 기존 파일 삭제"""
        if self.pk:
            old_instance = ChapterVideo.objects.get(pk=self.pk)
            if old_instance.video_url and old_instance.video_url != self.video_url:
                delete_file_from_ncp(old_instance.video_url.name)  # 기존 파일 삭제

        super().save(*args, **kwargs)  # 새로운 파일 저장

    def delete(self, *args, **kwargs):
        """NCP Object Storage에서도 파일 삭제"""
        if self.video_url:
            delete_file_from_ncp(self.video_url.name)  # 파일 삭제 실행
        super().delete(*args, **kwargs)

    class Meta:
        db_table = "chapter_video"


class ProgressTracking(BaseModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, null=True)
    chapter_video = models.ForeignKey(ChapterVideo, on_delete=models.CASCADE)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_completed = models.BooleanField(default=False)  # 강의 완료 여부
    last_watched_time = models.FloatField(default=0.0)  # 마지막 시청 시간 (초 단위)

    class Meta:
        db_table = "progress_tracking"
        unique_together = ("student", "chapter_video")

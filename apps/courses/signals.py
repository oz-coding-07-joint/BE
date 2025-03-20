from django.core.cache import cache
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.common.utils import redis_client  # utils.py에서 redis_client 가져오기
from apps.courses.models import ChapterVideo, Lecture, LectureChapter, ProgressTracking


def clear_lecture_chapter_cache(lecture_id):
    """해당 강의(lecture_id)와 관련된 챕터 데이터의 Redis 캐시 삭제"""
    cache_key = f"lecture_chapters:{lecture_id}"
    redis_client.delete(cache_key)


# LectureChapter 추가/수정/삭제 시 캐시 삭제
@receiver(post_save, sender=LectureChapter)
@receiver(post_delete, sender=LectureChapter)
def handle_lecture_chapter_change(sender, instance, **kwargs):
    clear_lecture_chapter_cache(instance.lecture_id)


# ChapterVideo 추가/수정/삭제 시 캐시 삭제 (LectureChapter와 연관됨)
@receiver(post_save, sender=ChapterVideo)
@receiver(post_delete, sender=ChapterVideo)
def handle_chapter_video_change(sender, instance, **kwargs):
    clear_lecture_chapter_cache(instance.lecture_chapter.lecture_id)


# Lecture 추가/수정/삭제 시 캐시 삭제 (Lecture 자체가 변경될 경우)
@receiver(post_save, sender=Lecture)
@receiver(post_delete, sender=Lecture)
def handle_lecture_change(sender, instance, **kwargs):
    clear_lecture_chapter_cache(instance.id)


def clear_student_lecture_cache(student_id):
    """학생의 강의 목록 캐시 삭제"""
    cache_key = f"student_{student_id}_lectures"
    cache.delete(cache_key)
    print(f"[Redis] 캐시 삭제됨: {cache_key}")  # 삭제 확인용 로그


@receiver(pre_save, sender=ProgressTracking)
def track_is_completed_change(sender, instance, **kwargs):
    """is_completed 변경 여부를 추적하여 플래그 설정"""
    if instance.pk:  # 기존 데이터가 존재하는 경우에만 비교
        try:
            old_instance = ProgressTracking.objects.get(pk=instance.pk)
            instance._is_completed_was = old_instance.is_completed  # 기존 값 저장
        except ProgressTracking.DoesNotExist:
            instance._is_completed_was = None


@receiver(post_save, sender=ProgressTracking)
def handle_progress_tracking_change(sender, instance, **kwargs):
    """is_completed 값이 변경된 경우에만 Redis 캐시 삭제"""
    if hasattr(instance, "_is_completed_was") and instance._is_completed_was != instance.is_completed:
        clear_student_lecture_cache(instance.student.id)


@receiver(post_delete, sender=ProgressTracking)
def handle_progress_tracking_delete(sender, instance, **kwargs):
    """ProgressTracking 삭제 시 캐시 삭제"""
    clear_student_lecture_cache(instance.student.id)

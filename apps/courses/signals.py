from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.utils import redis_client  # utils.py에서 redis_client 가져오기
from apps.courses.models import ChapterVideo, Lecture, LectureChapter


def clear_lecture_chapter_cache(lecture_id):
    """해당 강의(lecture_id)와 관련된 챕터 데이터의 Redis 캐시 삭제"""
    cache_key = f"lecture_chapters:{lecture_id}"
    redis_client.delete(cache_key)
    print(f"[Redis] 캐시 삭제됨: {cache_key}")  # 로그 출력 (확인용)


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

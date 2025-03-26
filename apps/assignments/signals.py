from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from apps.common.utils import redis_client

from .models import Assignment


@receiver(pre_save, sender=Assignment)
def clear_assignment_cache_pre_save(sender, instance, **kwargs):
    """저장 전 chapter_video 변경 시 이전 lecture_chapter 캐시를 삭제.

    기존 Assignment 인스턴스와 비교하여 chapter_video가 변경된 경우
    이전 lecture_chapter와 연관된 Redis 캐시를 삭제.

    Args:
        sender (Model): Assignment 모델 클래스.
        instance (Assignment): 저장될 Assignment 인스턴스.
        **kwargs: 추가 인자.
    """

    if instance.pk:
        try:
            old_instance = Assignment.objects.get(pk=instance.pk)
            if old_instance.chapter_video_id != instance.chapter_video_id:
                # 이전 chapter_video에 연결된 lecture_chapter의 캐시 삭제
                old_cache_key = f"assignments_{old_instance.chapter_video.lecture_chapter.id}"
                redis_client.delete(old_cache_key)
        except Assignment.DoesNotExist:
            pass


@receiver([post_save, post_delete], sender=Assignment)
def clear_assignment_cache(sender, instance, **kwargs):
    """Assignment 모델 변경 시, 관련 Redis 캐시를 삭제.

    Args:
        sender (Model): Assignment 모델.
        instance (Assignment): 변경된 Assignment 인스턴스.
        **kwargs: 추가 인자.
    """
    lecture_chapter_id = instance.chapter_video.lecture_chapter.id
    cache_key = f"assignments_{lecture_chapter_id}"
    redis_client.delete(cache_key)

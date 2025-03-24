from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.utils import redis_client

from .models import Assignment


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

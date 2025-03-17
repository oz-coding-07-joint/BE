from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.common.utils import redis_client

from .models import Assignment


@receiver([post_save, post_delete], sender=Assignment)
def clear_assignment_cache(sender, instance, **kwargs):
    # 과제가 속한 강의 챕터 ID를 가져옵니다.
    lecture_chapter_id = instance.chapter_video.lecture_chapter.id
    cache_key = f"assignments_{lecture_chapter_id}"
    redis_client.delete(cache_key)

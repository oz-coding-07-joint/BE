from django.db.models.signals import post_delete, pre_delete
from django.dispatch import receiver

from apps.courses.models import Lecture, ProgressTracking
from apps.registrations.models import Enrollment
from apps.reviews.models import Review
from apps.users.models import User


@receiver(pre_delete, sender=User)
def delete_related_table(sender, instance, **kwargs):
    # user 삭제 전에 one to one table과 관련된 ProgressTracking 삭제
    ProgressTracking.objects.filter(student__user=instance).delete()
    Enrollment.objects.filter(student__user=instance).delete()
    Review.objects.filter(student__user=instance).delete()
    Lecture.objects.filter(student__user=instance).delete()

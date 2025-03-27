from django.db.models.signals import pre_delete
from django.dispatch import receiver

from apps.courses.models import Lecture, ProgressTracking
from apps.registrations.models import Enrollment
from apps.reviews.models import Review
from apps.users.models import User


@receiver(pre_delete, sender=User)
def delete_related_table(sender, instance, **kwargs):
    # 유저가 학생(Student)인 경우
    if hasattr(instance, "student"):
        pt = ProgressTracking.objects.filter(student=instance.student)
        em = Enrollment.objects.filter(student=instance.student)
        review = Review.objects.filter(student=instance.student)
        
        if pt.exists():
            pt.delete()
        if em.exists():
            em.delete()
        if review.exists():
            review.delete()

    # 유저가 강사(Instructor)인 경우
    if hasattr(instance, "instructor"):
        lecture = Lecture.objects.filter(student=instance.student)
        
        if lecture.exists():
            lecture.delete()

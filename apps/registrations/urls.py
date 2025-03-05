from django.urls import path

from .views import (
    EnrollmentInProgressView,
    EnrollmentRegistrationView,
)

urlpatterns = [
    # 수강 신청
    path("enrollment/<int:class_id>/", EnrollmentRegistrationView.as_view(), name="enrollment-create"),
    # 수강중인 수업 조회
    path("enrollment/in-progress", EnrollmentInProgressView.as_view(), name="enrollment-in-progress"),
]

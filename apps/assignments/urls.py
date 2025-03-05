from django.urls import path

from .views import AssignmentCommentView, AssignmentView

urlpatterns = [
    # 강의 챕터별 과제 목록 조회
    path("<int:lecture_chapter_id>/", AssignmentView.as_view(), name="assignment-list"),
    # 강의 과제 제출, 수강생 과제 및 피드백 목록 조회
    path("assignment-comment/<int:assignment_id>/", AssignmentCommentView.as_view(), name="assignment-comment-submit"),
]

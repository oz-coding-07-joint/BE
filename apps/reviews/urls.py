from django.urls import path

from .views import MyReviewListView, ReviewView

urlpatterns = [
    # 후기 등록 및 조회
    path("<int:lecture_id>/", ReviewView.as_view(), name="review"),
    # 내가 작성한 후기 조회
    path("<int:student_id>/", MyReviewListView.as_view(), name="my-review"),
]

from django.urls import path

from apps.courses import views

urlpatterns = [
    path("lecture/", views.LectureListView.as_view(), name="lecture"),
    path("lecture/<lecture_id>/", views.LectureDetailView.as_view()),
    path("lecture_chapter/<lecture_id>/", views.LectureChapterListView.as_view()),
    path("chapter_video/<chapter_video_id>/state/", views.ChapterVideoProgressView.as_view()),
    path("chapter_video/<chapter_video_id>/progress/", views.ChapterVideoProgressUpdateView.as_view()),
    path("chapter_video/<chapter_video_id>/", views.ChapterVideoDetailView.as_view()),
]

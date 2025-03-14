from django.urls import path

from apps.courses import views

urlpatterns = [
    path("lecture/", views.LectureListView.as_view(), name="lecture"),
    path("lecture/<lecture_id>/", views.LectureDetailView.as_view()),
    path("lecture_chapter/<lecture_id>/", views.LectureChapterListView.as_view()),
    path(
        "chapter_video/<chapter_video_id>/progress/",
        views.ChapterVideoProgressCreateView.as_view(),
        name="chapter-video-progress-create",
    ),
    path(
        "chapter_video/<chapter_video_id>/progress/update/",
        views.ChapterVideoProgressUpdateView.as_view(),
        name="chapter-video-progress-update",
    ),
    path("chapter_video/<chapter_video_id>/", views.ChapterVideoDetailView.as_view()),
]

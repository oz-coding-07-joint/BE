from django.urls import path

from apps.courses import views

urlpatterns = [
    path("lecture/", views.LectureListView.as_view(), name="lecture"),
    path("lecture/<int:lecture_id>/", views.LectureDetailView.as_view()),
    path("lecture_chapter/<int:lecture_id>/", views.LectureChapterListView.as_view()),
    path(
        "chapter_video/<int:chapter_video_id>/state/",
        views.ChapterVideoProgressRetrieveView.as_view(),
        name="chapter_video_state",
    ),
    path(
        "chapter_video/<int:chapter_video_id>/progress/",
        views.ChapterVideoProgressCreateView.as_view(),
        name="chapter-video-progress-create",
    ),
    path(
        "chapter_video/<int:chapter_video_id>/progress/update/",
        views.ChapterVideoProgressUpdateView.as_view(),
        name="chapter-video-progress-update",
    ),
    path("chapter_video/<int:chapter_video_id>/", views.ChapterVideoDetailView.as_view()),
]

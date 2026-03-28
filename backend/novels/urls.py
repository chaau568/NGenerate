from django.urls import path
from . import views

urlpatterns = [
    path("", views.library, name="library"), # library
    path("create/", views.create_novel, name="create_novel"), # create new novel
    path("<int:novel_id>/", views.novel_detail, name="novel_detail"), # view novel detail
    path("<int:novel_id>/chapters/", views.create_chapter, name="create_chapter"), # create new chapter in novel
    path("chapters/<int:chapter_id>/", views.chapter_detail, name="chapter_detail"), # view chapter detail
    path("<int:novel_id>/characters/", views.novel_characters, name="novel_characters"), # view character detail
    path("<int:novel_id>/retry-upload/<int:notification_id>/", views.retry_upload, name="retry_upload",),
    path("<int:novel_id>/fix-chapters/", views.fix_chapters_batch, name="fix_chapters_batch"),
]

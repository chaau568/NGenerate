from django.urls import path
from . import views

urlpatterns = [
    
    # Create
    path("create/<int:novel_id>/", views.create_session, name="create-session"),

    # Summary
    path("summary/analyze/<int:session_id>/", views.summary_analyze, name="summary-analyze"),
    path("summary/generate/<int:session_id>/", views.summary_generate, name="summary-generate"),

    # Modify Session
    path("edit/<int:session_id>/", views.edit_session, name="edit-session"),

    # Start
    path("analyze/<int:session_id>/start/", views.start_analysis, name="analyze-start"),
    path("generate/<int:session_id>/start/", views.start_generation, name="generate-start"),
    path("retry/<int:session_id>/", views.retry_session, name="retry-session"),

    # History & Detail
    path("draft-tasks/", views.draft_tasks, name="draft-tasks"),
    path("current-tasks/", views.current_tasks, name="current-tasks"),
    path("finished-tasks/", views.finished_tasks, name="finished-tasks"),
    path("detail/<int:session_id>/", views.view_detail, name="history-detail"),
    path("data/<int:session_id>/", views.session_data, name="session-data"), 
    path("delete/<int:session_id>/", views.delete_session, name="delete-session"),
    path("project/", views.project_list, name="project-list"),
    path("project/<int:session_id>/", views.project_delete, name="project-delete"),

    # Sentence edit
    path("data/<int:session_id>/sentence/<int:sentence_id>/", views.update_sentence, name="update-sentence"),
    path("emotion-choices/", views.emotion_choices, name="emotion-choices"),
    
    # Character
    path("character/<int:character_id>/", views.delete_character, name="delete-character"),
]
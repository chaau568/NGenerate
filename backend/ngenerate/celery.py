import os
from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ngenerate.settings")

app = Celery("ngenerate")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.task_queues = (
    Queue("analysis_queue"),
    Queue("generation_queue"),
    Queue("upload_queue"),
)

app.conf.task_routes = {
    "ngenerate_sessions.tasks.run_analysis_task": {"queue": "analysis_queue"},
    "ngenerate_sessions.tasks.run_generation_task": {"queue": "generation_queue"},
    "novels.tasks.process_uploaded_file_task": {"queue": "upload_queue"},
}
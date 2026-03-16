import os
import requests
from celery import shared_task
from django.conf import settings
from novels.models import Novel
from notifications.models import Notification


@shared_task(bind=True, max_retries=3)
def process_uploaded_file_task(self, novel_id, file_path, notification_id):

    file_path = os.path.abspath(file_path)

    notification = Notification.objects.get(id=notification_id)

    try:

        novel = Novel.objects.get(id=novel_id)

        url = f"{settings.AI_API_URL}/preprocess/novel"

        print("UPLOAD FILE:", file_path)
        print("FILE SIZE:", os.path.getsize(file_path))

        with open(file_path, "rb") as f:
            resp = requests.post(url, files={"file": f}, timeout=settings.AI_TIMEOUT)

        resp.raise_for_status()

        chapters = resp.json()["chapters"]

        if not chapters:
            raise ValueError("No content extracted")

        story_list = [c["story"] for c in chapters]

        novel.bulk_add_chapters(story_list)

        notification.status = "success"
        notification.message = "File processed successfully"
        notification.save(update_fields=["status", "message", "updated_at"])

        if os.path.exists(file_path):
            os.remove(file_path)

        return "success"

    except Exception as e:

        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)

        notification.status = "error"
        notification.message = str(e)
        notification.save(update_fields=["status", "message", "updated_at"])

        if os.path.exists(file_path):
            os.remove(file_path)

        return "failed"

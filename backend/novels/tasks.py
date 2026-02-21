import os
from celery import shared_task
from django.conf import settings
from novels.models import Novel
from novels.services.data_preprocessing import DataPreprocessing
from notifications.models import Notification


@shared_task(bind=True)
def process_uploaded_file_task(self, novel_id, file_path, notification_id):
    
    notification = Notification.objects.get(id=notification_id)

    try:
        novel = Novel.objects.get(id=novel_id)

        processor = DataPreprocessing(
            poppler_path=settings.POPPLER_PATH
        )

        chapters = processor.run(file_path)

        if not chapters:
            raise ValueError("No content extracted")

        if len(chapters) > 1:
            novel.bulk_add_chapters(chapters)
        else:
            novel.add_chapter(chapters[0]["story"])

        notification.status = "success"
        notification.message = "File processed successfully"
        notification.save(update_fields=["status", "message", "updated_at"])

        return "success"

    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)

        notification.status = "error"
        notification.message = str(e)
        notification.save(update_fields=["status", "message", "updated_at"])

        return "failed"

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
import os
import requests
from celery import shared_task
from django.conf import settings
from novels.models import Novel, Chapter
from notifications.models import Notification


@shared_task(bind=True, max_retries=3)
def process_uploaded_file_task(
    self, novel_id, file_bytes, file_name, content_type, notification_id
):

    notification = Notification.objects.get(id=notification_id)

    try:
        novel = Novel.objects.get(id=novel_id)

        url = f"{settings.AI_API_URL}/preprocess/novel"

        resp = requests.post(
            url,
            files={"file": (file_name, bytes(file_bytes), content_type)},
            timeout=settings.AI_TIMEOUT,
        )

        resp.raise_for_status()
        chapters = resp.json()["chapters"]

        if not chapters:
            raise ValueError("No content extracted")

        novel.bulk_add_chapters([c["story"] for c in chapters])

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


@shared_task(bind=True, max_retries=2, queue="fix_text_queue")
def fix_chapters_batch_task(self, chapter_ids, notification_id, total_cost):
    notification = Notification.objects.get(id=notification_id)

    try:
        chapters = Chapter.objects.filter(id__in=chapter_ids).order_by("order")
        total = chapters.count()

        if total == 0:
            raise Exception("No chapters found")

        for index, chapter in enumerate(chapters):
            notification.message = f"กำลังแก้ไขตอนที่ {index + 1}/{total}: {chapter.title}"
            notification.save(update_fields=["message", "updated_at"])

            success = chapter.fix_story_with_ai()

            if not success:
                raise Exception(f"Fix failed at chapter {chapter.id}")

        notification.status = "success"
        notification.message = f"แก้ไขคำผิดเสร็จสิ้น {total} ตอน (ใช้ {total_cost} credits)"
        notification.save(update_fields=["status", "message", "updated_at"])

        return "success"

    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)

        notification.status = "error"
        notification.message = f"เกิดข้อผิดพลาด: {str(e)}"
        notification.save(update_fields=["status", "message", "updated_at"])

        return "failed"

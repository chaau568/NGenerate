import os
import requests
from django.urls import reverse
from celery import shared_task
from django.conf import settings
from notifications.models import Notification


@shared_task(bind=True, max_retries=3)
def process_uploaded_file_task(
    self, novel_id, file_bytes, file_name, content_type, notification_id
):
    notification = Notification.objects.get(id=notification_id)

    try:
        callback_path = reverse("runpod_webhook")
        callback_url = f"{settings.SITE_URL}{callback_path}"

        url = f"{settings.AI_API_URL}/preprocess/novel"

        resp = requests.post(
            url,
            files={"file": (file_name, bytes(file_bytes), content_type)},
            data={"novel_id": str(novel_id), "callback_url": callback_url},
            timeout=120,
        )

        resp.raise_for_status()

        notification.message = "กำลังประมวลผล OCR ในเบื้องหลัง (อาจใช้เวลาสักครู่)..."
        notification.save(update_fields=["message", "updated_at"])

        return "upload_success_processing_started"

    except Exception as e:
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e, countdown=10)

        notification.status = "error"
        notification.message = f"เกิดข้อผิดพลาดในการส่งไฟล์: {str(e)}"
        notification.save(update_fields=["status", "message", "updated_at"])
        return "failed"


# import os
# import requests
# from celery import shared_task
# from django.conf import settings
# from novels.models import Novel, Chapter
# from notifications.models import Notification


# @shared_task(bind=True, max_retries=3)
# def process_uploaded_file_task(
#     self, novel_id, file_bytes, file_name, content_type, notification_id
# ):

#     notification = Notification.objects.get(id=notification_id)

#     try:
#         novel = Novel.objects.get(id=novel_id)

#         url = f"{settings.AI_API_URL}/preprocess/novel"

#         resp = requests.post(
#             url,
#             files={"file": (file_name, bytes(file_bytes), content_type)},
#             timeout=settings.AI_TIMEOUT,
#         )

#         resp.raise_for_status()
#         chapters = resp.json()["chapters"]

#         if not chapters:
#             raise ValueError("No content extracted")

#         novel.bulk_add_chapters([c["story"] for c in chapters])

#         notification.status = "success"
#         notification.message = "File processed successfully"
#         notification.save(update_fields=["status", "message", "updated_at"])

#         return "success"

#     except Exception as e:
#         if self.request.retries < self.max_retries:
#             raise self.retry(exc=e, countdown=10)

#         notification.status = "error"
#         notification.message = str(e)
#         notification.save(update_fields=["status", "message", "updated_at"])
#         return "failed"


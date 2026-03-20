from notifications.models import Notification


def get_or_create_notification(user, session, task_type, message, generation_run=None):

    if task_type == "generation" and generation_run:
        notification, _ = Notification.objects.get_or_create(
            generation_run=generation_run,
            task_type="generation",
            defaults={
                "user": user,
                "session": session,
                "message": message,
                "status": "processing",
            },
        )
    else:
        notification, _ = Notification.objects.get_or_create(
            session=session,
            task_type=task_type,
            defaults={
                "user": user,
                "message": message,
                "status": "processing",
            },
        )

    return notification


def update_notification(notification, status=None, message=None):

    if status:
        notification.status = status

    if message:
        notification.message = message

    notification.is_read = False
    notification.save(update_fields=["status", "message", "is_read", "updated_at"])

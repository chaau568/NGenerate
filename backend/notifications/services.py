from notifications.models import Notification


def get_or_create_notification(user, session, task_type, message):

    notification, _ = Notification.objects.get_or_create(
        user=user,
        session=session,
        task_type=task_type,
        defaults={
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

from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Notification

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = (
        Notification.objects.filter(user=request.user)
        .select_related("session", "novel")
        .order_by("-created_at")
    )

    data = []
    for n in notifications:
        item = {
            "id": n.id,
            "task_type": n.task_type,
            "status": n.get_effective_status(),
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at,
            "type": "session" if n.session else "novel",
            "ref_id": n.session.id if n.session else n.novel.id,
        }
        data.append(item)

    return Response({"notifications": data})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    data = {
        "id": notification.id,
        "task_type": notification.task_type,
        "task_name": (
            f"{notification.task_type.capitalize()} Task"
            if notification.task_type
            else "Task"
        ),
        "status": notification.get_effective_status(),
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "processing": None,
        "session_info": None,
        "novel_info": None,
        "session_id": notification.session_id,
        "novel_id": notification.novel_id,
        "session_name": notification.session.name if notification.session else None,
    }

    if notification.session:
        session = notification.session
        phase = notification.task_type

        if phase == "analysis":
            steps = session.processing_steps.filter(phase="analysis").order_by("order")
            total = steps.count()
            success_count = steps.filter(status="success").count()
            phase_progress = round((success_count / total) * 100) if total > 0 else 0

            if session.status == "analyzed":
                phase_progress = 100

            data["processing"] = {
                "overall_progress": phase_progress,
                "started_at": session.created_at,
                "steps": [
                    {
                        "id": step.id,
                        "name": step.name,
                        "status": (
                            "analyzed"
                            if step.status == "success"
                            else (
                                "analyzing"
                                if step.status == "processing"
                                else "fail" if step.status == "failed" else "pending"
                            )
                        ),
                        "started_at": step.start_at,
                        "finished_at": step.finish_at,
                        "error_message": step.error_message or None,
                    }
                    for step in steps
                ],
            }

        elif phase == "generation":
            generation_run = notification.generation_run
            if generation_run:
                steps = generation_run.processing_steps.all().order_by("order")

                if generation_run.status == "generating":
                    total = steps.count()
                    success_count = steps.filter(status="success").count()
                    phase_progress = (
                        round((success_count / total) * 100) if total > 0 else 0
                    )
                    phase_progress = min(phase_progress, 99)
                else:
                    phase_progress = generation_run.get_progress_percentage()

                data["processing"] = {
                    "overall_progress": phase_progress,
                    "started_at": generation_run.created_at,
                    "steps": [
                        {
                            "id": step.id,
                            "name": step.name,
                            "status": (
                                "generated"
                                if step.status == "success"
                                else (
                                    "generating"
                                    if step.status == "processing"
                                    else (
                                        "fail" if step.status == "failed" else "pending"
                                    )
                                )
                            ),
                            "started_at": step.start_at,
                            "finished_at": step.finish_at,
                            "error_message": step.error_message or None,
                        }
                        for step in steps
                    ],
                }

    elif notification.novel:
        data["novel_info"] = {
            "novel_id": notification.novel.id,
            "title": notification.novel.title,
        }

    return Response({"data": data}, status=status.HTTP_200_OK)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def notification_delete(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def notification_update(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )

    data = request.data
    updated_fields = []

    if "is_read" in data:
        notification.is_read = data["is_read"]
        updated_fields.append("is_read")

    if "status" in data:
        if data["status"] not in dict(Notification.STATUS_CHOICES):
            return Response(
                {"error": "Invalid status"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        notification.status = data["status"]
        updated_fields.append("status")

    if "message" in data:
        notification.message = data["message"]
        updated_fields.append("message")

    if updated_fields:
        notification.save(update_fields=updated_fields)

    return Response({"success": True}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notification_is_read(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({"count": count})

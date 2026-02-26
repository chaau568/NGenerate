from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Notification

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


@extend_schema(
    summary="ดึงรายการแจ้งเตือนทั้งหมด",
    description="แสดงรายการแจ้งเตือนสถานะการทำงาน (Processing, Success, Error) ของผู้ใช้",
    responses={
        200: inline_serializer(
            name="NotificationListResponse",
            fields={
                "notifications": serializers.ListField(
                    child=inline_serializer(
                        name="NotificationListItem",
                        fields={
                            "id": serializers.IntegerField(),
                            "task_name": serializers.CharField(),
                            "status": serializers.CharField(),
                            "message": serializers.CharField(),
                            "is_read": serializers.BooleanField(),
                            "created_at": serializers.DateTimeField(),
                            "type": serializers.ChoiceField(
                                choices=["session", "novel"]
                            ),
                            "ref_id": serializers.IntegerField(),
                        },
                    )
                )
            },
        )
    },
    tags=["Notifications"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by(
        "-created_at"
    )

    data = []
    for n in notifications:
        item = {
            "id": n.id,
            "task_name": n.task_name,
            "status": n.status,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at,
            "type": "session" if n.session else "novel",
            "ref_id": n.session.id if n.session else n.novel.id,
        }
        data.append(item)

    return Response({"notifications": data})


@extend_schema(
    summary="ดูรายละเอียดการแจ้งเตือน",
    description="ดึงรายละเอียดเชิงลึกของการแจ้งเตือน และทำเครื่องหมายว่าอ่านแล้ว (is_read=True) โดยอัตโนมัติ",
    responses={
        200: inline_serializer(
            name="NotificationDetailResponse",
            fields={
                "data": inline_serializer(
                    name="NotificationDetailData",
                    fields={
                        "id": serializers.IntegerField(),
                        "task_name": serializers.CharField(),
                        "status": serializers.CharField(),
                        "message": serializers.CharField(),
                        "is_read": serializers.BooleanField(),
                        "created_at": serializers.DateTimeField(),
                        "session_info": serializers.DictField(
                            required=False, allow_null=True
                        ),
                        "novel_info": serializers.DictField(
                            required=False, allow_null=True
                        ),
                    },
                )
            },
        )
    },
    tags=["Notifications"],
)
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
        "task_name": notification.task_name,
        "status": notification.status,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "processing": None,
        "session_info": None,
        "novel_info": None,
    }

    if notification.session:
        session = notification.session
        steps = session.processing_steps.all().order_by("phase", "order")

        def map_status(step_status):
            return {
                "pending": "pending",
                "processing": "analyzing",
                "success": "analyzed",
                "failed": "fail",
            }.get(step_status, "pending")

        data["processing"] = {
            "overall_progress": session.get_progress_percentage(),
            "started_at": session.created_at,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "status": map_status(step.status),
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


@extend_schema(
    summary="ลบการแจ้งเตือน",
    description="ลบ notification ออกจากระบบ",
    responses={204: None},
    tags=["Notifications"],
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def notification_delete(request, notification_id):
    notification = get_object_or_404(
        Notification, id=notification_id, user=request.user
    )
    notification.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(
    summary="อัปเดตการแจ้งเตือน",
    description="อัปเดตสถานะหรือข้อความของ notification",
    request=inline_serializer(
        name="NotificationUpdateRequest",
        fields={
            "is_read": serializers.BooleanField(required=False),
            "status": serializers.ChoiceField(
                choices=["processing", "success", "error"], required=False
            ),
            "message": serializers.CharField(required=False),
        },
    ),
    responses={200: None},
    tags=["Notifications"],
)
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

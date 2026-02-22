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
            name='NotificationListResponse',
            fields={
                "notifications": serializers.ListField(
                    child=inline_serializer(
                        name='NotificationListItem',
                        fields={
                            "id": serializers.IntegerField(),
                            "task_name": serializers.CharField(),
                            "status": serializers.CharField(),
                            "message": serializers.CharField(),
                            "is_read": serializers.BooleanField(),
                            "created_at": serializers.DateTimeField(),
                            "type": serializers.ChoiceField(choices=['session', 'novel']),
                            "ref_id": serializers.IntegerField()
                        }
                    )
                )
            }
        )
    },
    tags=["Notifications"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by("-created_at")
    
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
            "ref_id": n.session.id if n.session else n.novel.id 
        }
        data.append(item)
        
    return Response({"notifications": data})

@extend_schema(
    summary="ดูรายละเอียดการแจ้งเตือน",
    description="ดึงรายละเอียดเชิงลึกของการแจ้งเตือน และทำเครื่องหมายว่าอ่านแล้ว (is_read=True) โดยอัตโนมัติ",
    responses={
        200: inline_serializer(
            name='NotificationDetailResponse',
            fields={
                "data": inline_serializer(
                    name='NotificationDetailData',
                    fields={
                        "id": serializers.IntegerField(),
                        "task_name": serializers.CharField(),
                        "status": serializers.CharField(),
                        "message": serializers.CharField(),
                        "is_read": serializers.BooleanField(),
                        "created_at": serializers.DateTimeField(),
                        "session_info": serializers.DictField(required=False, allow_null=True),
                        "novel_info": serializers.DictField(required=False, allow_null=True),
                    }
                )
            }
        )
    },
    tags=["Notifications"]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_detail(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        
    data = {
        "id": notification.id,
        "task_name": notification.task_name,
        "status": notification.status,
        "message": notification.message,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
        "session_info": None,
        "novel_info": None
    }
    
    if notification.session:
        session = notification.session
        steps = session.processing_steps.all().order_by('phase', 'order')
        
        data["session_info"] = {
            "session_id": session.id,
            "session_name": session.name,
            "overall_status": session.status,
            "progress_percentage": session.get_progress_percentage(),
            "steps": [
                {
                    "phase": step.phase,
                    "name": step.name,
                    "status": step.status,
                    "error": step.error_message,
                    "start_at": step.start_at,
                    "finish_at": step.finish_at,
                }
                for step in steps
            ]
        }
        
    elif notification.novel:
        data["novel_info"] = {
            "novel_id": notification.novel.id,
            "title": notification.novel.title,
        }
        
    return Response({"data": data}, status=status.HTTP_200_OK)
import os
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from .models import Novel, Chapter
from notifications.models import Notification
from .tasks import process_uploaded_file_task


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def library(request):
    novels = Novel.objects.filter(user=request.user).order_by('-updated_at')
    
    total_novels = novels.count()
    
    data = {
        "total_novels": total_novels,
        "chapters": [
            {
                "id": n.id,
                "title": n.title,
                "cover": n.cover.url if n.cover else None,
                "total_chapters": n.get_total_chapters(),
                "analyzed_chapters": n.get_total_analyzed_chapters(),
                "created_at": n.created_at,
                "updated_at": n.updated_at,
            }
            for n in novels
        ]
    }
    
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_novel(request):
    title = request.data.get('title')
    cover = request.FILES.get('cover')
    
    if not title:
        return Response({"error": "Please provide title"}, status=status.HTTP_400_BAD_REQUEST)
    
    novel = Novel.objects.create(
        title=title,
        user=request.user,
        cover=cover
    )
    
    return Response({
        "id": novel.id,
        "title": novel.title,
        "cover": novel.cover.url if novel.cover else None
    }, status=status.HTTP_201_CREATED)

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def novel_detail(request, novel_id):
    novel = get_object_or_404(
        Novel,
        id=novel_id,
        user=request.user
    )
    
    if request.method == 'PUT':
        novel.edit(
            title=request.data.get('title'),
            cover=request.data.get('cover')
        )
    
    if request.method == 'DELETE':
        novel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    return Response({
        "id": novel.id,
        "title": novel.title,
        "cover": novel.cover.url if novel.cover else None,
        "chapters": [
            {
                "id": c.id,
                "order": c.order,
                "title": c.title,
                "is_analyzed": c.is_analyzed
            }
            for c in novel.get_chapters()
        ]
    }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chapter(request, novel_id):
    novel = get_object_or_404(Novel, id=novel_id, user=request.user)
    
    # 1. รับข้อมูลจาก Frontend
    story_text = request.data.get('story')
    file_obj = request.FILES.get('file')

    # --- กรณีที่ 1: ส่งมาเป็น Text (บันทึกทันที) ---
    if story_text:
        if isinstance(story_text, str):
            chapters_to_add = [story_text]
        elif isinstance(story_text, list):
            chapters_to_add = story_text
        else:
            return Response({"error": "Invalid text format"}, status=status.HTTP_400_BAD_REQUEST)
            
        new_chapters = novel.bulk_add_chapters(chapters_to_add)
        return Response({
            "status": "completed",
            "message": f"Created {len(new_chapters)} chapters from text",
            "chapters": [{"id": c.id, "title": c.title} for c in new_chapters]
        }, status=status.HTTP_201_CREATED)

    # --- กรณีที่ 2: ส่งมาเป็น File (บันทึกทันที) ---
    if file_obj:
        file_path = default_storage.save(
            f'uploads/{file_obj.name}',
            ContentFile(file_obj.read())
        )

        absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        notification = Notification.objects.create(
            user=request.user,
            novel=novel,
            task_name="Upload & Preprocessing",
            status="processing",
            message=f"Processing file {file_obj.name}"
        )

        process_uploaded_file_task.delay(
            novel.id,
            absolute_path,
            notification.id
        )

        return Response({
            "status": "processing",
            "message": "File is being processed in background."
        }, status=status.HTTP_202_ACCEPTED)

    return Response({"error": "No content or file provided"}, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def chapter_detail(request, chapter_id):
    chapter = get_object_or_404(
        Chapter,
        id=chapter_id,
        novel__user=request.user
    )

    if request.method == 'DELETE':
        chapter.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    if request.method == 'PUT':
        chapter.edit(
            title=request.data.get('title'),
            story=request.data.get('story')
        )

    return Response({
        "id": chapter.id,
        "title": chapter.title,
        "story": chapter.story,
        "order": chapter.order
    }, status=status.HTTP_200_OK)

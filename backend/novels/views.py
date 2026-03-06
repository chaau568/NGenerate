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

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers


@extend_schema(
    summary="ดึงรายการนิยายทั้งหมดในชั้นหนังสือ",
    responses={
        200: inline_serializer(
            name="LibraryResponse",
            fields={
                "total_novels": serializers.IntegerField(),
                "chapters": serializers.ListField(child=serializers.DictField()),
            },
        )
    },
    tags=["Library"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def library(request):
    novels = Novel.objects.filter(user=request.user).order_by("-updated_at")

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
        ],
    }

    return Response(data)


@extend_schema(
    summary="สร้างนิยายเรื่องใหม่",
    request={
        "multipart/form-data": inline_serializer(
            name="CreateNovelRequest",
            fields={
                "title": serializers.CharField(),
                "cover": serializers.ImageField(required=False),
            },
        )
    },
    responses={
        201: inline_serializer(
            name="CreateNovelResponse",
            fields={
                "id": serializers.IntegerField(),
                "title": serializers.CharField(),
                "cover": serializers.URLField(),
            },
        )
    },
    tags=["Library"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_novel(request):
    title = request.data.get("title")
    cover = request.FILES.get("cover")

    if not title:
        return Response(
            {"error": "Please provide title"}, status=status.HTTP_400_BAD_REQUEST
        )

    novel = Novel.objects.create(title=title, user=request.user, cover=cover)

    return Response(
        {
            "id": novel.id,
            "title": novel.title,
            "cover": novel.cover.url if novel.cover else None,
        },
        status=status.HTTP_201_CREATED,
    )


@extend_schema(
    summary="รายละเอียดนิยาย / แก้ไข / ลบ",
    methods=["GET", "PUT", "DELETE"],
    request=inline_serializer(
        name="UpdateNovelRequest",
        fields={
            "title": serializers.CharField(required=False),
            "cover": serializers.ImageField(required=False),
        },
    ),
    tags=["Library"],
)
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def novel_detail(request, novel_id):
    novel = get_object_or_404(Novel, id=novel_id, user=request.user)

    if request.method == "PUT":
        novel.edit(title=request.data.get("title"), cover=request.data.get("cover"))

    if request.method == "DELETE":
        novel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    characters = novel.get_characters().prefetch_related("image_assets")

    return Response(
        {
            "id": novel.id,
            "title": novel.title,
            "cover": novel.cover.url if novel.cover else None,
            "chapters": [
                {
                    "id": c.id,
                    "order": c.order,
                    "title": c.title,
                    "is_analyzed": c.is_analyzed,
                }
                for c in novel.get_chapters()
            ],
            "characters": [
                {
                    "name": char.name,
                    "master_image_path": (
                        img.image.url if (img := char.image_assets.first()) else None
                    ),
                }
                for char in characters
            ],
        },
        status=status.HTTP_200_OK,
    )


extend_schema(
    summary="รายการตัวละครในนิยาย",
    methods=["GET"],
    responses=inline_serializer(
        name="NovelCharacterResponse",
        many=True,
        fields={
            "id": serializers.IntegerField(),
            "name": serializers.CharField(),
            "appearance": serializers.CharField(allow_null=True),
            "outfit": serializers.CharField(allow_null=True),
            "sex": serializers.CharField(allow_null=True),
            "age": serializers.IntegerField(allow_null=True),
            "race": serializers.CharField(allow_null=True),
            "base_personality": serializers.CharField(allow_null=True),
            "master_image_path": serializers.CharField(allow_null=True),
        },
    ),
    tags=["Library"],
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def novel_characters(request, novel_id):
    novel = get_object_or_404(Novel, id=novel_id, user=request.user)
    characters = novel.get_characters()

    characters = novel.get_characters().prefetch_related("image_assets")

    return Response(
        [
            {
                "id": char.id,
                "name": char.name,
                "appearance": char.appearance,
                "outfit": char.outfit,
                "sex": char.sex,
                "age": char.age,
                "race": char.race,
                "base_personality": char.base_personality,
                "master_image_path": (
                    img.image.url if (img := char.image_assets.first()) else None
                ),
            }
            for char in characters
        ],
        status=status.HTTP_200_OK,
    )


@extend_schema(
    summary="เพิ่มบทนิยาย (จากข้อความ หรือ อัปโหลดไฟล์)",
    description="ส่ง 'story' เป็น String/Array เพื่อบันทึกทันที หรือส่ง 'file' เพื่อประมวลผลใน Background (Celery)",
    request={
        "multipart/form-data": inline_serializer(
            name="CreateChapterRequest",
            fields={
                "story": serializers.CharField(
                    required=False, help_text="เนื้อหานิยาย หรือ List ของเนื้อหา"
                ),
                "file": serializers.FileField(
                    required=False, help_text="ไฟล์ .txt หรือ .docx สำหรับนำเข้า"
                ),
            },
        )
    },
    responses={
        201: inline_serializer(
            name="ChapterCreated",
            fields={
                "status": serializers.CharField(),
                "chapters": serializers.ListField(child=serializers.DictField()),
            },
        ),
        202: inline_serializer(
            name="ChapterProcessing",
            fields={
                "status": serializers.CharField(),
                "message": serializers.CharField(),
            },
        ),
    },
    tags=["Chapters"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_chapter(request, novel_id):
    novel = get_object_or_404(Novel, id=novel_id, user=request.user)

    # 1. รับข้อมูลจาก Frontend
    story_text = request.data.get("story")
    file_obj = request.FILES.get("file")

    # --- กรณีที่ 1: ส่งมาเป็น Text (บันทึกทันที) ---
    if story_text:
        if isinstance(story_text, str):
            chapters_to_add = [story_text]
        elif isinstance(story_text, list):
            chapters_to_add = story_text
        else:
            return Response(
                {"error": "Invalid text format"}, status=status.HTTP_400_BAD_REQUEST
            )

        new_chapters = novel.bulk_add_chapters(chapters_to_add)
        return Response(
            {
                "status": "completed",
                "message": f"Created {len(new_chapters)} chapters from text",
                "chapters": [{"id": c.id, "title": c.title} for c in new_chapters],
            },
            status=status.HTTP_201_CREATED,
        )

    # --- กรณีที่ 2: ส่งมาเป็น File (บันทึกทันที) ---
    if file_obj:
        file_path = default_storage.save(
            f"uploads/{file_obj.name}", ContentFile(file_obj.read())
        )

        absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)

        notification = Notification.objects.create(
            user=request.user,
            novel=novel,
            task_name="Upload & Preprocessing",
            status="processing",
            message=f"Processing file {file_obj.name}",
        )

        process_uploaded_file_task.delay(novel.id, absolute_path, notification.id)

        return Response(
            {
                "status": "processing",
                "message": "File is being processed in background.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response(
        {"error": "No content or file provided"}, status=status.HTTP_400_BAD_REQUEST
    )


@extend_schema(
    summary="รายละเอียดบทนิยาย / แก้ไข / ลบ",
    methods=["GET", "PUT", "DELETE"],
    tags=["Chapters"],
)
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def chapter_detail(request, chapter_id):
    chapter = get_object_or_404(Chapter, id=chapter_id, novel__user=request.user)

    if request.method == "DELETE":
        chapter.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    if request.method == "PUT":
        chapter.edit(title=request.data.get("title"), story=request.data.get("story"))

    return Response(
        {
            "id": chapter.id,
            "title": chapter.title,
            "story": chapter.story,
            "order": chapter.order,
            "is_analyzed": chapter.is_analyzed,
        },
        status=status.HTTP_200_OK,
    )

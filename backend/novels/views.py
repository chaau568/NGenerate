import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404


from .models import Novel, Chapter
from notifications.models import Notification
from .tasks import process_uploaded_file_task

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from utils.file_url import build_file_url


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
                "cover": build_file_url(n.get_cover_url()),
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

    novel = Novel.objects.create(title=title, user=request.user)

    if cover:
        novel.set_cover(cover)

    return Response(
        {
            "id": novel.id,
            "title": novel.title,
            "cover": build_file_url(novel.get_cover_url()),
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
        title = request.data.get("title")
        cover = request.FILES.get("cover")

        if title:
            novel.title = title

        if cover:
            novel.set_cover(cover)

        novel.save()

    if request.method == "DELETE":
        novel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    characters = novel.get_characters().select_related("asset")

    return Response(
        {
            "id": novel.id,
            "title": novel.title,
            "cover": build_file_url(novel.cover) if novel.cover else None,
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
                    "master_image_path": char.get_master_image_url(),
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

    characters = novel.get_characters().select_related("asset")

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
                "master_image_path": char.get_master_image_url(),
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

    story_text = request.data.get("story")
    file_obj = request.FILES.get("file")

    # ---------------- TEXT ----------------

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

    # ---------------- FILE ----------------

    if file_obj:
        notification = Notification.objects.create(
            user=request.user,
            novel=novel,
            task_type="upload",
            message=f"Processing file {file_obj.name}",
        )

        file_bytes = file_obj.read()
        file_name = file_obj.name
        content_type = file_obj.content_type

        process_uploaded_file_task.delay(
            novel.id,
            file_bytes,
            file_name,
            content_type,
            notification.id,
        )

        return Response(
            {
                "status": "processing",
                "message": "File is being processed in background.",
            },
            status=status.HTTP_202_ACCEPTED,
        )

    return Response(
        {"error": "No content or file provided"},
        status=status.HTTP_400_BAD_REQUEST,
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retry_upload(request, novel_id, notification_id):
    get_object_or_404(
        __import__("novels.models", fromlist=["Novel"]).Novel,
        id=novel_id,
        user=request.user,
    )

    notification = get_object_or_404(
        Notification,
        id=notification_id,
        user=request.user,
        novel_id=novel_id,
        task_type="upload",
    )

    if notification.status != "error":
        return Response(
            {"error": "Only failed upload notifications can be retried."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    file_path = notification.file_path

    if not file_path or not os.path.exists(file_path):
        return Response(
            {
                "error": "Original file no longer available. Please re-upload the file.",
                "code": "FILE_NOT_FOUND",
            },
            status=status.HTTP_410_GONE,
        )

    notification.status = "processing"
    notification.message = "Re-processing file (retry)..."
    notification.save(update_fields=["status", "message"])

    process_uploaded_file_task.delay(
        notification.novel_id,
        file_path,
        notification.id,
    )

    return Response(
        {
            "message": "Upload retry started.",
            "notification_id": notification.id,
        },
        status=status.HTTP_202_ACCEPTED,
    )


@api_view(["POST"])
@permission_classes([AllowAny])
def runpod_webhook(request):
    data = request.data
    novel_id = data.get("novel_id")
    status_ai = data.get("status")

    if not novel_id:
        print("[ERROR] Missing novel_id")
        return Response({"error": "Missing novel_id"}, status=400)

    try:
        novel = Novel.objects.get(id=novel_id)

        notification = Notification.objects.filter(
            novel=novel, task_type="upload"
        ).last()

        # =========================
        # CASE 1: BATCH (🔥 สำคัญสุด)
        # =========================
        if status_ai == "processing_batch":
            chapters = data.get("chapters", [])

            print(f"[BATCH] Incoming: {len(chapters)} chapters")

            if chapters:
                created = novel.bulk_add_chapters(chapters)

                print(f"[BATCH] Created: {len(created)}")
                print(f"[BATCH] Total in DB: {novel.chapters.count()}")

                if notification:
                    notification.message = (
                        f"กำลังประมวลผล... นำเข้าแล้ว {novel.chapters.count()} ตอน"
                    )
                    notification.save(update_fields=["message", "updated_at"])

            return Response({"status": "batch_saved"})

        # =========================
        # CASE 2: ITEM (fallback)
        # =========================
        elif status_ai == "processing_item":
            chapter_data = data.get("chapter")

            print("[ITEM] Incoming:", chapter_data)

            if chapter_data:
                created = novel.bulk_add_chapters([chapter_data])

                print(f"[ITEM] Created: {len(created)}")
                print(f"[ITEM] Total in DB: {novel.chapters.count()}")

                if notification:
                    notification.message = (
                        f"กำลังประมวลผล... นำเข้าแล้ว {novel.chapters.count()} ตอน"
                    )
                    notification.save(update_fields=["message", "updated_at"])

            return Response({"status": "item_saved"})

        # =========================
        # CASE 3: SUCCESS
        # =========================
        elif status_ai == "success":
            print("[SUCCESS] Processing completed")

            if notification:
                total_chapters = novel.chapters.count()
                notification.status = "success"
                notification.message = f"ประมวลผลเสร็จสมบูรณ์! ทั้งหมด {total_chapters} ตอน"
                notification.save()

            return Response({"status": "completed"})

        # =========================
        # CASE 4: ERROR
        # =========================
        elif status_ai == "error":
            print("[ERROR FROM AI]:", data.get("message"))

            if notification:
                notification.status = "error"
                notification.message = data.get("message", "AI processing failed")
                notification.save()

            return Response({"status": "error_logged"})

        # =========================
        # UNKNOWN STATUS
        # =========================
        else:
            print("[WARNING] Unknown status:", status_ai)
            return Response({"status": "ignored", "reason": "unknown status"})

    except Novel.DoesNotExist:
        print("[ERROR] Novel not found:", novel_id)
        return Response({"error": "Novel not found"}, status=404)

    except Exception as e:
        print("[FATAL ERROR]:", str(e))
        return Response({"error": str(e)}, status=500)

from django.shortcuts import get_object_or_404
from django.db import transaction

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .models import Session
from novels.models import Novel, Chapter
from users.models import UserCredit
from payments.models import CreditLog
from notifications.models import Notification

from .tasks import run_analysis_task, run_generation_task


# =====================================================
# CREATE SESSION
# =====================================================


@extend_schema(
    summary="สร้าง Session ใหม่ (Analysis หรือ Full)",
    request=inline_serializer(
        name="CreateSessionRequest",
        fields={
            "chapter_ids": serializers.ListField(child=serializers.IntegerField()),
            "session_type": serializers.ChoiceField(choices=["analysis", "full"]),
            "name": serializers.CharField(required=False),
        },
    ),
    responses={
        201: inline_serializer(
            name="CreateSessionResponse",
            fields={
                "session_id": serializers.IntegerField(),
                "session_name": serializers.CharField(),
                "status": serializers.CharField(),
                "chapter_count": serializers.IntegerField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_session(request, novel_id):

    novel = get_object_or_404(Novel, id=novel_id, user=request.user)

    chapter_ids = request.data.get("chapter_ids", [])
    session_type = request.data.get("session_type", "analysis")
    name = request.data.get("name")

    if session_type not in dict(Session.SESSION_TYPE_CHOICES):
        return Response(
            {"error": "Invalid session type"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not chapter_ids:
        return Response(
            {"error": "At least one chapter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    chapters = Chapter.objects.filter(id__in=chapter_ids, novel=novel)

    if chapters.count() != len(chapter_ids):
        return Response(
            {"error": "Some chapters are invalid"}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():

        session = Session.objects.create(
            novel=novel, session_type=session_type, name=name or ""
        )

        session.chapters.set(chapters)

        if not name:
            ordered = chapters.order_by("order")
            first = ordered.first()
            last = ordered.last()

            session.name = (
                f"Session: {novel.title} chapter#{first.order} - chapter#{last.order}"
            )[:255]

            session.save(update_fields=["name"])

    return Response(
        {
            "session_id": session.id,
            "session_name": session.name,
            "status": session.status,
            "chapter_count": chapters.count(),
        },
        status=status.HTTP_201_CREATED,
    )


# =====================================================
# SUMMARY ANALYZE
# =====================================================


@extend_schema(
    summary="ดูสรุปค่าใช้จ่ายก่อนเริ่มการวิเคราะห์ (Analysis)",
    responses={
        200: inline_serializer(
            name="SummaryAnalyzeResponse",
            fields={
                "details": serializers.DictField(),
                "summary": serializers.DictField(),
                "status": serializers.CharField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_analyze(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    chapters = session.chapters.order_by("order")
    total_chapters = chapters.count()
    required_credit = session.calculate_analysis_credit()
    wallet = UserCredit.objects.get(user=request.user)

    return Response(
        {
            "details": {
                "session_name": session.name,
                "chapters": [
                    {"id": c.id, "order": c.order, "title": c.title} for c in chapters
                ],
            },
            "summary": {
                "session_type": session.session_type,
                "chapter_count": total_chapters,
                "credit_per_chapter": (
                    required_credit // total_chapters if total_chapters else 0
                ),
                "total_credit_required": required_credit,
                "credits_remaining": wallet.available,
            },
            "status": session.status,
        }
    )


@extend_schema(
    summary="แก้ไข Session (เฉพาะสถานะ Draft)",
    request=inline_serializer(
        name="EditSessionRequest",
        fields={
            "chapter_ids": serializers.ListField(
                child=serializers.IntegerField(), required=False
            ),
            "name": serializers.CharField(required=False),
        },
    ),
    responses={
        200: inline_serializer(
            name="EditSessionResponse",
            fields={
                "session_id": serializers.IntegerField(),
                "session_name": serializers.CharField(),
                "status": serializers.CharField(),
                "chapter_count": serializers.IntegerField(),
            },
        ),
        400: inline_serializer(
            name="EditSessionError", fields={"error": serializers.CharField()}
        ),
    },
    tags=["Sessions"],
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def edit_session(request, session_id):

    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if session.status != "draft":
        return Response(
            {"error": "Only draft sessions can be edited"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    chapter_ids = request.data.get("chapter_ids")
    name = request.data.get("name")

    with transaction.atomic():
        if name is not None:
            session.name = name

        if chapter_ids is not None:
            if not chapter_ids:
                return Response(
                    {"error": "At least one chapter is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            chapters = Chapter.objects.filter(id__in=chapter_ids, novel=session.novel)

            if chapters.count() != len(chapter_ids):
                return Response(
                    {"error": "Some chapters are invalid"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            session.chapters.set(chapters)

        session.save()

    return Response(
        {
            "session_id": session.id,
            "session_name": session.name,
            "status": session.status,
            "chapter_count": session.chapters.count(),
        }
    )


@extend_schema(
    summary="เริ่มกระบวนการวิเคราะห์ (ตัด Credit และเริ่ม Task)",
    responses={
        201: inline_serializer(
            name="StartAnalysisResponse",
            fields={
                "status": serializers.CharField(),
                "locked_credits": serializers.IntegerField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_analysis(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if session.status == "analyzing":
        return Response(
            {"error": "Analysis already running"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            session.start_analysis()

            run_analysis_task.delay(session.id)
        # session.refresh_from_db()
        return Response(
            {"status": session.status, "locked_credits": session.locked_credits},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# SUMMARY GENERATE
# =====================================================


@extend_schema(
    summary="ดูสรุปค่าใช้จ่ายก่อนเริ่มการสร้าง (Generation)",
    description="คำนวณ Credit จากจำนวนประโยค, โปรไฟล์ตัวละคร และจำนวนภาพประกอบที่ต้องสร้าง",
    responses={
        200: inline_serializer(
            name="SummaryGenerateResponse",
            fields={
                "details": serializers.DictField(),
                "summary": inline_serializer(
                    name="GenerationSummary",
                    fields={
                        "sentence_count": serializers.IntegerField(),
                        "character_count": serializers.IntegerField(),
                        "scene_count": serializers.IntegerField(),
                        "total_credit_required": serializers.IntegerField(),
                        "credits_remaining": serializers.IntegerField(),
                    },
                ),
                "status": serializers.CharField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_generate(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    # Must be full session
    if session.session_type != "full":
        return Response(
            {"error": "This session does not allow generation"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Must finish analysis first
    if not session.is_analysis_done:
        return Response(
            {"error": "Analysis not completed"}, status=status.HTTP_400_BAD_REQUEST
        )

    # Must be in analyzed state
    if session.status != "analyzed":
        return Response(
            {"error": "Session is not ready for generation"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    required_credit = session.calculate_generation_credit()
    wallet = UserCredit.objects.get(user=request.user)

    return Response(
        {
            "details": {
                "session_name": session.name,
            },
            "summary": {
                "sentence_count": session.sentences.count(),
                "character_count": session.novel.character_profiles.count(),
                "scene_count": session.illustrations.count(),
                "total_credit_required": required_credit,
                "credits_remaining": wallet.available,
            },
            "status": session.status,
        }
    )


@extend_schema(
    summary="เริ่มกระบวนการสร้าง (ตัด Credit และเริ่มสร้างภาพ/วิดีโอ)",
    responses={
        201: inline_serializer(
            name="StartGenerationResponse",
            fields={
                "status": serializers.CharField(),
                "locked_credits": serializers.IntegerField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_generation(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if session.status == "generating":
        return Response(
            {"error": "Generation already running"}, status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            session.start_generation()

            run_generation_task.delay(session.id)
        # session.refresh_from_db()
        return Response(
            {"status": session.status, "locked_credits": session.locked_credits},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# HISTORY
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_tasks(request):
    sessions = (
        Session.objects.filter(
            novel__user=request.user, status__in=["analyzing", "generating"]
        )
        .prefetch_related("processing_steps")
        .order_by("-created_at")
    )

    current_tasks = []

    for s in sessions:
        current_tasks.append(
            {
                "session_id": s.id,
                "novel_id": s.novel.id,
                "session_name": s.name,
                "status": s.status,
                "type": s.session_type,
                "progress": s.get_progress_percentage(),
            }
        )

    return Response(
        {"current_tasks": current_tasks},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def finished_tasks(request):
    sessions = (
        Session.objects.filter(
            novel__user=request.user, status__in=["analyzed", "generated"]
        )
        .select_related("novel")
        .prefetch_related("videos")
        .order_by("-created_at")
    )

    analysis_history = []
    generation_history = []

    for s in sessions:
        latest_video = s.videos.order_by("-version").first()

        base_data = {
            "session_id": s.id,
            "novel_id": s.novel.id,
            "session_name": s.name,
            "status": s.status,
            "type": s.session_type,
            "created_at": s.created_at,
            "cover": s.novel.cover.url if s.novel.cover else None,
        }

        if s.status == "analyzed":
            analysis_history.append(
                {
                    **base_data,
                    "analysis_finished_at": s.analysis_finished_at,
                }
            )

        elif s.status == "generated":
            generation_history.append(
                {
                    **base_data,
                    "video_id": latest_video.id if latest_video else None,
                    "version": latest_video.version if latest_video else None,
                    "file_size": latest_video.file_size if latest_video else 0.0,
                    "generation_finished_at": s.generation_finished_at,
                }
            )

    return Response(
        {
            "analysis_history": analysis_history,
            "generation_history": generation_history,
        },
        status=status.HTTP_200_OK,
    )


@extend_schema(summary="ลบ Session", responses={204: None}, tags=["Sessions"])
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)
    session.delete()
    return Response({"message": "Session deleted"}, status=status.HTTP_204_NO_CONTENT)


# =====================================================
# VIEW DETAIL (PIPELINE)
# =====================================================


@extend_schema(
    summary="ดูความคืบหน้าของ Pipeline (Processing Steps)",
    responses={
        200: inline_serializer(
            name="ViewDetailResponse",
            fields={
                "session_name": serializers.CharField(),
                "status": serializers.CharField(),
                "overall_progress": serializers.IntegerField(),
                "steps": serializers.ListField(child=serializers.DictField()),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_detail(request, session_id):
    session = get_object_or_404(
        Session.objects.prefetch_related("processing_steps"),
        id=session_id,
        novel__user=request.user,
    )

    steps = session.processing_steps.all().order_by("order")

    return Response(
        {
            "session_name": session.name,
            "status": session.status,
            "overall_progress": session.get_progress_percentage(),
            "started_at": session.created_at,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "started_at": s.start_at,
                    "finished_at": s.finish_at,
                    "error_message": s.error_message if s.status == "failed" else None,
                }
                for s in steps
            ],
        }
    )


# =====================================================
# TRANSACTION
# =====================================================


@extend_schema(
    summary="ประวัติการใช้ Credit",
    responses={
        200: inline_serializer(
            name="TransactionHistoryResponse",
            fields={
                "transactions": serializers.ListField(child=serializers.DictField())
            },
        )
    },
    tags=["History"],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def transaction_history(request):

    credit_logs = CreditLog.objects.filter(user=request.user).order_by("-created_at")

    data = [
        {
            "date": log.created_at,
            "type": log.type,
            "session_id": log.session.id if log.session else None,
            "amount": log.amount,
        }
        for log in credit_logs
    ]

    return Response({"transactions": data})


# =====================================================
# RETRY
# =====================================================


@extend_schema(
    summary="เริ่มการทำงานใหม่กรณีที่ Failed",
    description="ล้างข้อมูลเดิมใน Session และเริ่มกระบวนการใหม่ตามจุดที่ค้างอยู่",
    responses={
        200: inline_serializer(
            name="RetryResponse",
            fields={
                "message": serializers.CharField(),
                "status": serializers.CharField(),
            },
        )
    },
    tags=["Sessions"],
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retry_session(request, session_id):

    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if session.status != "failed":
        return Response(
            {"error": "Only failed sessions can retry"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ----------------------------------
    # CLEAR SESSION DATA
    # ----------------------------------

    session.sentences.all().delete()
    session.illustrations.all().delete()
    session.processing_steps.all().delete()

    session.status = "draft"
    session.error_message = None
    session.locked_credits = 0
    session.save()

    # ----------------------------------
    # RESTART
    # ----------------------------------

    if not session.is_analysis_done:
        session.start_analysis()
        run_analysis_task.delay(session.id)
    else:
        session.start_generation()
        run_generation_task.delay(session.id)

    return Response({"message": "Retry started", "status": session.status})

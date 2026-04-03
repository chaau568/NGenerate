from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers

from .models import Session, GenerationRun, Sentence, CharacterProfile
from novels.models import Novel, Chapter
from users.models import UserCredit
from asset.models import CharacterAsset, NarratorVoice, IllustrationImage
from utils.file_url import build_file_url
from utils.runpod_storage import delete_runpod_folder

from .tasks import run_analysis_task, run_generation_task
from .services.convert import ConvertTextToJson

import logging

logger = logging.getLogger(__name__)

from collections import defaultdict


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
    style = request.data.get("style", "chinese-modern")

    if session_type not in dict(Session.SESSION_TYPE_CHOICES):
        return Response(
            {"error": "Invalid session type"}, status=status.HTTP_400_BAD_REQUEST
        )

    if not chapter_ids:
        return Response(
            {"error": "At least one chapter is required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if style not in dict(Session.STYLE_CHOICES):
        return Response({"error": "Invalid style"}, status=status.HTTP_400_BAD_REQUEST)

    chapters = Chapter.objects.filter(id__in=chapter_ids, novel=novel)

    if chapters.count() != len(chapter_ids):
        return Response(
            {"error": "Some chapters are invalid"}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        session = Session.objects.create(
            novel=novel,
            session_type=session_type,
            name=name or "",
            style=style,
        )
        session.chapters.set(chapters)

        if not name:
            ordered = chapters.order_by("order")
            first = ordered.first()
            last = ordered.last()
            if len(chapters) == 1:
                session.name = f"Session: {novel.title} chapter#{first.order}"[:255]
            else:
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_analyze(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    chapters = session.chapters.order_by("order")
    total_chapters = chapters.count()
    required_credit = session.calculate_analysis_credit()
    wallet, _ = UserCredit.objects.get_or_create(user=request.user)

    return Response(
        {
            "details": {
                "session_name": session.name,
                "style": session.style,
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
            "style_choices": session.get_style_choices(),
            "status": session.status,
        }
    )


# =====================================================
# EDIT SESSION
# =====================================================


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
    style = request.data.get("style")

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

        if style is not None:
            if style not in dict(Session.STYLE_CHOICES):
                return Response(
                    {"error": "Invalid style"}, status=status.HTTP_400_BAD_REQUEST
                )
            session.style = style

        session.save()

    return Response(
        {
            "session_id": session.id,
            "session_name": session.name,
            "status": session.status,
            "chapter_count": session.chapters.count(),
        }
    )


# =====================================================
# START ANALYSIS
# =====================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_analysis(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if session.status not in ["draft", "failed"]:
        return Response(
            {"error": "Session must be in draft or failed state"}, status=400
        )

    try:
        with transaction.atomic():
            session.start_analysis()
            transaction.on_commit(
                lambda: run_analysis_task.apply_async(
                    args=[session.id],
                    queue="analysis_queue",
                    priority=5,
                )
            )

        return Response(
            {"status": session.status, "locked_credits": session.locked_credits},
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# SUMMARY GENERATE
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary_generate(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if not session.is_analysis_done:
        return Response(
            {"error": "Analysis not completed"}, status=status.HTTP_400_BAD_REQUEST
        )

    if session.status != "analyzed":
        return Response(
            {"error": "Session is not ready for generation"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # ป้องกัน generate ซ้อนกัน
    if session.generation_runs.filter(status="generating").exists():
        return Response(
            {"error": "Generation is already in progress"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    required_credit = session.calculate_generation_credit()
    wallet, _ = UserCredit.objects.get_or_create(user=request.user)

    return Response(
        {
            "details": {"session_name": session.name},
            "summary": {
                "sentence_count": session.sentences.count(),
                "character_count": session.scene_characters.count(),
                "scene_count": session.illustrations.count(),
                "total_credit_required": required_credit,
                "credits_remaining": wallet.available,
            },
            "generation_history": [
                {
                    "version": r.version,
                    "status": r.status,
                    "style": r.style,
                    "created_at": r.created_at,
                    "generation_finished_at": r.generation_finished_at,
                }
                for r in session.generation_runs.order_by("-version")
            ],
            "status": session.status,
        }
    )


# =====================================================
# START GENERATION  ← จุดสำคัญ: สร้าง GenerationRun ใหม่ทุกครั้ง
# =====================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_generation(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if not session.is_analysis_done:
        return Response({"error": "Analysis not completed"}, status=400)

    if session.status != "analyzed":
        return Response({"error": "Session must be analyzed first"}, status=400)

    if session.generation_runs.filter(status="generating").exists():
        return Response({"error": "Generation is already in progress"}, status=400)

    try:
        with transaction.atomic():
            # สร้าง GenerationRun ใหม่ทุกครั้งที่กด Generate
            run = GenerationRun.create_next(session)
            run.start()

            run_id = run.id
            transaction.on_commit(
                lambda: run_generation_task.apply_async(
                    args=[run_id],
                    queue="generation_queue",
                    priority=7,
                )
            )

        return Response(
            {
                "generation_run_id": run.id,
                "version": run.version,
                "status": run.status,
                "locked_credits": run.locked_credits,
            },
            status=status.HTTP_201_CREATED,
        )
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# HISTORY / PROJECT LIST
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def draft_tasks(request):
    sessions = (
        Session.objects.filter(novel__user=request.user, status="draft")
        .select_related("novel")
        .order_by("-created_at")
    )
    return Response(
        {"draft_tasks": [{"session_id": s.id} for s in sessions]},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_tasks(request):
    # analyzing sessions
    analyzing_sessions = (
        Session.objects.filter(novel__user=request.user, status="analyzing")
        .prefetch_related("processing_steps")
        .order_by("-created_at")
    )

    # generating runs
    generating_runs = (
        GenerationRun.objects.filter(
            session__novel__user=request.user,
            status="generating",
        )
        .select_related("session__novel")
        .prefetch_related("processing_steps")
        .order_by("-created_at")
    )

    current_tasks = []

    for s in analyzing_sessions:
        current_tasks.append(
            {
                "session_id": s.id,
                "novel_id": s.novel.id,
                "session_name": s.name,
                "status": s.status,
                "type": "analysis",
                "progress": s.get_progress_percentage(),
            }
        )

    for run in generating_runs:
        current_tasks.append(
            {
                "session_id": run.session.id,
                "novel_id": run.session.novel.id,
                "session_name": run.session.name,
                "generation_run_id": run.id,
                "version": run.version,
                "status": run.status,
                "type": "generation",
                "progress": run.get_progress_percentage(),
            }
        )

    return Response({"current_tasks": current_tasks}, status=status.HTTP_200_OK)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def finished_tasks(request):
    sessions = (
        Session.objects.filter(
            novel__user=request.user,
            status__in=["analyzed", "failed"],
        )
        .select_related("novel")
        .prefetch_related("generation_runs__video")
        .order_by("-created_at")
    )

    analysis_history = []
    generation_history = []
    failed_history = []

    for s in sessions:
        base_data = {
            "session_id": s.id,
            "novel_id": s.novel.id,
            "session_name": s.name,
            "status": s.status,
            "type": s.session_type,
            "created_at": s.created_at,
            "cover": build_file_url(s.novel.get_cover_url()),
        }

        if s.status == "analyzed":
            analysis_history.append(
                {
                    **base_data,
                    "analysis_finished_at": s.analysis_finished_at,
                }
            )

            for run in s.generation_runs.all():
                if run.status == "generated":
                    video = getattr(run, "video", None)
                    generation_history.append(
                        {
                            **base_data,
                            "generation_run_id": run.id,
                            "version": run.version,
                            "video_id": video.id if video else None,
                            "file_size": video.file_size if video else 0.0,
                            "generation_finished_at": run.generation_finished_at,
                        }
                    )
                elif run.status == "failed":
                    failed_history.append(
                        {
                            **base_data,
                            "generation_run_id": run.id,
                            "version": run.version,
                            "failed_type": "generation",
                            "generation_finished_at": run.generation_finished_at,
                        }
                    )

        elif s.status == "failed":
            failed_history.append(
                {
                    **base_data,
                    "failed_type": "analysis",
                }
            )

    return Response(
        {
            "analysis_history": analysis_history,
            "generation_history": generation_history,
            "failed_history": failed_history,
        },
        status=status.HTTP_200_OK,
    )


# =====================================================
# DELETE SESSION
# =====================================================


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_generation_run(request, run_id):
    run = get_object_or_404(
        GenerationRun,
        id=run_id,
        session__novel__user=request.user,
    )

    session = run.session

    folder_path = (
        f"user_data/user_{session.novel.user_id}"
        f"/novel_{session.novel_id}"
        f"/session_{session.id}"
        f"/v{run.version}"
    )
    try:
        delete_runpod_folder(folder_path)
    except Exception as e:
        logger.warning(f"Failed to delete RunPod folder: {e}")

    if run.locked_credits > 0:
        from payments.services.credit_service import CreditService

        CreditService.refund_credit(
            user=session.novel.user,
            amount=run.locked_credits,
            session=session,
            session_name=session.name,
        )

    run.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    session = get_object_or_404(
        Session,
        id=session_id,
        novel__user=request.user,
    )

    is_generating = session.generation_runs.filter(status="generating").exists()

    if is_generating:
        return Response(
            {"error": "Session is currently generating. Please wait or cancel first."},
            status=status.HTTP_409_CONFLICT,
        )

    user_id = request.user.id
    novel_id = session.novel.id
    sid = session.id

    runpod_path = f"user_data/user_{user_id}/novel_{novel_id}/session_{sid}"
    try:
        delete_runpod_folder(runpod_path)
    except Exception as e:
        logger.warning(f"Failed to delete RunPod folder for session {sid}: {e}")

    session.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================
# VIEW DETAIL (PIPELINE)
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def view_detail(request, session_id):
    session = get_object_or_404(
        Session.objects.prefetch_related("processing_steps"),
        id=session_id,
        novel__user=request.user,
    )

    # Analysis steps
    analysis_steps = session.processing_steps.all().order_by("order")

    # Generation runs + steps
    generation_runs_data = []
    for run in session.generation_runs.prefetch_related("processing_steps").order_by(
        "-version"
    ):
        generation_runs_data.append(
            {
                "generation_run_id": run.id,
                "version": run.version,
                "status": run.status,
                "style": run.style,
                "progress": run.get_progress_percentage(),
                "created_at": run.created_at,
                "generation_finished_at": run.generation_finished_at,
                "steps": [
                    {
                        "id": s.id,
                        "name": s.name,
                        "status": s.status,
                        "started_at": s.start_at,
                        "finished_at": s.finish_at,
                        "error_message": (
                            s.error_message if s.status == "failed" else None
                        ),
                    }
                    for s in run.processing_steps.all().order_by("order")
                ],
            }
        )

    return Response(
        {
            "session_name": session.name,
            "status": session.status,
            "overall_progress": session.get_progress_percentage(),
            "started_at": session.created_at,
            "analysis_steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "status": s.status,
                    "started_at": s.start_at,
                    "finished_at": s.finish_at,
                    "error_message": s.error_message if s.status == "failed" else None,
                }
                for s in analysis_steps
            ],
            "generation_runs": generation_runs_data,
        }
    )


# =====================================================
# RETRY
# =====================================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def retry_session(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    with transaction.atomic():

        if not session.is_analysis_done:
            if session.status != "failed":
                return Response(
                    {"error": "Session is not in failed state"},
                    status=400,
                )

            session.processing_steps.all().delete()
            session.sentences.all().delete()
            session.scene_characters.all().delete()
            session.illustrations.all().delete()

            session.status = "draft"
            session.locked_credits = 0
            session.save(update_fields=["status", "locked_credits"])

            session.start_analysis()
            transaction.on_commit(
                lambda: run_analysis_task.apply_async(
                    args=[session.id],
                    queue="analysis_queue",
                    priority=5,
                )
            )
            message = "Analysis failed. Cleared all data and restarting analysis."

        else:
            if session.status != "analyzed":
                return Response(
                    {"error": "Session must be in analyzed state"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if session.generation_runs.filter(status="generating").exists():
                return Response(
                    {"error": "Generation is already in progress"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            failed_runs = session.generation_runs.filter(status="failed")
            for failed_run in failed_runs:
                failed_run.character_assets.all().delete()
                failed_run.voices.all().delete()
                failed_run.scene_images.all().delete()
                failed_run.processing_steps.all().delete()

                folder_path = (
                    f"user_data/user_{session.novel.user_id}"
                    f"/novel_{session.novel_id}"
                    f"/session_{session.id}"
                    f"/v{failed_run.version}"
                )
                try:
                    delete_runpod_folder(folder_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete RunPod folder v{failed_run.version}: {e}"
                    )

            run = GenerationRun.create_next(session)
            run.start()

            run_id = run.id
            transaction.on_commit(
                lambda: run_generation_task.apply_async(
                    args=[run_id],
                    queue="generation_queue",
                    priority=7,
                )
            )
            message = f"Starting new generation run v{run.version}."

    return Response({"message": message, "status": session.status})


# =====================================================
# PROJECT LIST (unified endpoint)
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def project_list(request):
    query_type = request.query_params.get("type", "current")

    if query_type == "current":
        return current_tasks(request)
    elif query_type == "finished":
        return finished_tasks(request)
    else:
        return Response({"error": "Invalid type"}, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def project_delete(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    try:
        folder_path = f"user_data/user_{session.novel.user_id}/novel_{session.novel_id}/session_{session.id}"
        delete_runpod_folder(folder_path)
    except Exception:
        pass

    session.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)


# =====================================================
# SESSION DATA (ANALYSIS + GENERATION)
# =====================================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_data(request, session_id):

    session = get_object_or_404(
        Session.objects.select_related("novel"),
        id=session_id,
        novel__user=request.user,
    )

    if not session.is_analysis_done:
        return Response(
            {"error": "Analysis not completed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # =====================
    # GENERATION RUN
    # =====================
    run_id = request.query_params.get("run_id")

    if run_id:
        generation_run = get_object_or_404(
            GenerationRun,
            id=run_id,
            session=session,
            status="generated",
        )
    else:
        generation_run = (
            session.generation_runs.filter(status="generated")
            .order_by("-version")
            .first()
        )

    is_generated = generation_run is not None

    # =====================
    # VOICE MAP  →  { sentence_id: url }
    # =====================
    voice_map = {}

    if is_generated:
        # ✅ filter ด้วย sentence_id__in เพื่อความแน่ใจ
        sentence_ids = list(session.sentences.values_list("id", flat=True))
        voice_assets = NarratorVoice.objects.filter(
            generation_run=generation_run,
            sentence_id__in=sentence_ids,
        ).values("sentence_id", "voice")

        for v in voice_assets:
            voice_map[v["sentence_id"]] = build_file_url(v["voice"])

    # =====================
    # SENTENCES MAP  →  { chapter_order: [sentence, ...] }
    # =====================
    sentences_qs = session.sentences.select_related("chapter").order_by(
        "chapter__order", "sentence_index"
    )

    sentences_map = defaultdict(list)

    for sent in sentences_qs:
        sentences_map[sent.chapter.order].append(
            {
                "id": sent.id,
                "sentence_index": sent.sentence_index,
                "sentence": sent.sentence,
                "tts_text": sent.tts_text,
                "voice": voice_map.get(sent.id),
            }
        )

    # =====================
    # CHARACTER IMAGE MAP  →  { (illustration_id, profile_id): url }
    # ✅ ใช้ composite key เพื่อไม่ให้ overwrite กัน
    # =====================
    character_image_map = {}

    if is_generated:
        character_assets = (
            CharacterAsset.objects.filter(
                generation_run=generation_run,
                scene_character__session=session,
            )
            .select_related("scene_character")
            .values(
                "scene_character__illustration_id",
                "scene_character__character_profile_id",
                "image",
            )
        )

        for asset in character_assets:
            key = (
                asset["scene_character__illustration_id"],
                asset["scene_character__character_profile_id"],
            )
            character_image_map[key] = build_file_url(asset["image"])

    # =====================
    # SCENE IMAGE MAP  →  { illustration_id: url }
    # =====================
    scene_image_map = {}

    if is_generated:

        scene_assets = IllustrationImage.objects.filter(
            generation_run=generation_run,
            illustration__session=session,
        ).values("illustration_id", "image")

        for sa in scene_assets:
            scene_image_map[sa["illustration_id"]] = build_file_url(sa["image"])

    # =====================
    # SCENES
    # =====================
    scenes_qs = (
        session.illustrations.select_related("chapter")
        .prefetch_related("scene_characters__character_profile")
        .order_by("chapter__order", "scene_index")
    )

    scenes_data = []

    for scene in scenes_qs:
        # -------- scene image --------
        scene_image = scene_image_map.get(scene.id)

        # -------- characters --------
        scene_characters = []
        for sc in scene.scene_characters.all():
            key = (scene.id, sc.character_profile_id)
            scene_characters.append(
                {
                    "id": sc.character_profile.id,
                    "name": sc.character_profile.name,
                    "action": sc.action,
                    "expression": sc.expression,
                    "image": character_image_map.get(key),  # ✅ composite key
                }
            )

        # -------- sentences --------
        chapter_sentences = sentences_map.get(scene.chapter.order, [])

        if scene.sentence_start is None or scene.sentence_end is None:
            scene_sentences = []
        else:
            scene_sentences = [
                s
                for s in chapter_sentences
                if scene.sentence_start <= s["sentence_index"] <= scene.sentence_end
            ]

        scenes_data.append(
            {
                "id": scene.id,
                "chapter_order": scene.chapter.order,
                "scene_index": scene.scene_index,
                "description": scene.scene_description,
                "image": scene_image,
                "characters": scene_characters,
                "sentences": scene_sentences,
            }
        )

    # =====================
    # RESPONSE
    # =====================
    return Response(
        {
            "session_id": session.id,
            "session_name": session.name,
            "session_type": session.session_type,
            "style": session.style,
            "status": session.status,
            "is_analysis_done": session.is_analysis_done,
            "is_generation_done": is_generated,
            "current_generation_run": (
                {
                    "id": generation_run.id,
                    "version": generation_run.version,
                    "style": generation_run.style,
                }
                if generation_run
                else None
            ),
            "generation_runs": [
                {
                    "id": r.id,
                    "version": r.version,
                    "status": r.status,
                    "style": r.style,
                    "generation_finished_at": r.generation_finished_at,
                }
                for r in session.generation_runs.order_by("-version")
            ],
            "scenes": scenes_data,
        }
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_sentence(request, session_id, sentence_id):

    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    if not session.is_analysis_done:
        return Response(
            {"error": "Analysis not completed"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    sentence = get_object_or_404(Sentence, id=sentence_id, session=session)

    allowed_fields = {"sentence", "tts_text"}
    update_data = {k: v for k, v in request.data.items() if k in allowed_fields}

    if not update_data:
        return Response(
            {"error": "No valid fields to update"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if "sentence" in update_data:
        if not update_data["sentence"].strip():
            return Response(
                {"error": "Sentence cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        converter = ConvertTextToJson()
        update_data["tts_text"] = converter.to_syllable_text(update_data["sentence"])

    for field, value in update_data.items():
        setattr(sentence, field, value)

    sentence.save(update_fields=list(update_data.keys()))

    return Response(
        {
            "id": sentence.id,
            "sentence": sentence.sentence,
            "tts_text": sentence.tts_text,
        },
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def emotion_choices(request):

    return Response({"emotions": []})


# =====================================================
# DELETE CHARACTER (LIBRARY)
# =====================================================


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_character(request, character_id):

    character = get_object_or_404(
        CharacterProfile, id=character_id, novel__user=request.user
    )

    character.delete()

    return Response(
        {"message": "Character deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )

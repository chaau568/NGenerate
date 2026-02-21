from django.shortcuts import get_object_or_404
from django.db import transaction

# DRF Imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Session
from novels.models import Novel, Chapter
from users.models import UserCredit
from payments.models import CreditLog
from notifications.models import Notification

from .tasks import run_analysis_task


# =====================================================
# SUMMARY ANALYZE
# =====================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_session(request, novel_id):

    novel = get_object_or_404(
        Novel,
        id=novel_id,
        user=request.user
    )

    chapter_ids = request.data.get("chapter_ids", [])
    session_type = request.data.get("session_type", "analysis")
    name = request.data.get("name")

    if session_type not in dict(Session.SESSION_TYPE_CHOICES):
        return Response(
            {"error": "Invalid session type"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not chapter_ids:
        return Response(
            {"error": "At least one chapter is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    chapters = Chapter.objects.filter(
        id__in=chapter_ids,
        novel=novel
    )

    if chapters.count() != len(chapter_ids):
        return Response(
            {"error": "Some chapters are invalid"},
            status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():

        session = Session.objects.create(
            novel=novel,
            session_type=session_type,
            name=name or ""
        )

        session.chapters.set(chapters)

        if not name:
            ordered = chapters.order_by("order")
            first = ordered.first()
            last = ordered.last()

            session.name = (f"Session: {novel.title} chapter#{first.order} - chapter#{last.order}")[:255]

            session.save(update_fields=["name"])

    return Response({
        "session_id": session.id,
        "session_name": session.name,
        "status": session.status,
        "chapter_count": chapters.count()
    }, status=status.HTTP_201_CREATED)

# =====================================================
# SUMMARY ANALYZE
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary_analyze(request, session_id):
    session = get_object_or_404(
        Session,
        id=session_id,
        novel__user=request.user
    )

    chapters = session.chapters.order_by("order")
    total_chapters = chapters.count()
    required_credit = session.calculate_analysis_credit()
    wallet = UserCredit.objects.get(user=request.user)

    return Response({
        "details": {
            "session_name": session.name,
            "chapters": [
                {
                    "id": c.id,
                    "order": c.order,
                    "title": c.title
                } for c in chapters
            ]
        },
        "summary": {
            "session_type": session.session_type,
            "chapter_count": total_chapters,
            "credit_per_chapter": (
                required_credit // total_chapters if total_chapters else 0
            ),
            "total_credit_required": required_credit,
            "credits_remaining": wallet.available
        },
        "status": session.status
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def edit_session(request, session_id):
    
    session = get_object_or_404(
        Session,
        id=session_id,
        novel__user=request.user
    )
    
    if session.status != "draft":
        return Response(
            {"error": "Only draft sessions can be edited"},
            status=status.HTTP_400_BAD_REQUEST
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
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            chapters = Chapter.objects.filter(
                id__in=chapter_ids,
                novel=session.novel
            )
            
            if chapters.count() != len(chapter_ids):
                return Response(
                    {"error": "Some chapters are invalid"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            session.chapters.set(chapters)
            
        session.save()
        
    return Response({
        "session_id": session.id,
        "session_name": session.name,
        "status": session.status,
        "chapter_count": session.chapters.count()
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_analysis(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)
    
    if session.status == "analyzing":
        return Response(
            {"error": "Analysis already running"},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        with transaction.atomic():
            session.start_analysis()
        
            notification = Notification.objects.create(
                user=session.novel.user,
                session=session,
                task_name="Analysis",
                status="processing",
                message=f"Analysis started for session '{session.name}'."
            )
            
            run_analysis_task.delay(session.id, notification.id)
        # session.refresh_from_db()
        return Response({
            "status": session.status,
            "locked_credits": session.locked_credits
        })
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# SUMMARY GENERATE
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def summary_generate(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)
    
    # Must be full session
    if session.session_type != "full":
        return Response(
            {"error": "This session does not allow generation"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Must finish analysis first
    if not session.is_analysis_done:
        return Response(
            {"error": "Analysis not completed"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Must be in analyzed state
    if session.status != "analyzed":
        return Response(
            {"error": "Session is not ready for generation"},
            status=status.HTTP_400_BAD_REQUEST
        )

    required_credit = session.calculate_generation_credit()
    wallet = UserCredit.objects.get(user=request.user)

    return Response({
        "details": {
            "session_name": session.name,
        },
        "summary": {
            "sentence_count": session.sentences.count(),
            "character_count": session.novel.character_profiles.count(),
            "scene_count": session.illustrations.count(),
            "total_credit_required": required_credit,
            "credits_remaining": wallet.available
        },
        "status": session.status
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_generation(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    try:
        session.start_generation()
        # run_generation_task.delay(session.id)
        return Response({"message": "Generation started"})
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# HISTORY
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def history(request):
    sessions = Session.objects.filter(
        novel__user=request.user
    ).prefetch_related('processing_steps').order_by("-created_at")

    current_tasks = []
    analyzed_history = []
    generated_history = []

    for s in sessions:
        # --- เรียกใช้ที่นี่ ---
        progress = s.get_progress_percentage() 

        base_data = {
            "session_id": s.id,
            "session_name": s.name,
            "status": s.status,
            "progress": progress,
        }

        if s.status in ["analyzing", "generating"]:
            current_tasks.append(base_data)
            
        elif s.status == "analyzed":
            analyzed_history.append(base_data)
            
        elif s.status == "generated":
            generated_history.append(base_data)

    return Response({
        "current_tasks": current_tasks,
        "analysis_history": analyzed_history,
        "generation_history": generated_history
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)
    session.delete()
    return Response({"message": "Session deleted"}, status=status.HTTP_204_NO_CONTENT)


# =====================================================
# VIEW DETAIL (PIPELINE)
# =====================================================
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_detail(request, session_id):
    session = get_object_or_404(Session, id=session_id, novel__user=request.user)
    steps = session.processing_steps.all()

    return Response({
        "session_name": session.name,
        "status": session.status,
        "overall_progress": session.get_progress_percentage(),
        "steps": [
            {
                "phase": s.phase,
                "name": s.name,
                "status": s.status,
                "error": s.error_message,
                "started_at": s.start_at,
                "finished_at": s.finish_at,
            }
            for s in steps
        ]
    })


# =====================================================
# TRANSACTION
# =====================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def transaction_history(request):

    credit_logs = CreditLog.objects.filter(
        user=request.user
    ).order_by("-created_at")

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

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def retry_session(request, session_id):

#     session = get_object_or_404(
#         Session,
#         id=session_id,
#         novel__user=request.user
#     )

#     if session.status != "failed":
#         return Response(
#             {"error": "Only failed sessions can retry"},
#             status=status.HTTP_400_BAD_REQUEST
#         )

#     # ----------------------------------
#     # CLEAR SESSION DATA
#     # ----------------------------------

#     session.sentences.all().delete()
#     session.illustrations.all().delete()
#     session.processing_steps.all().delete()

#     session.status = "draft"
#     session.error_message = None
#     session.locked_credits = 0
#     session.save()

#     # ----------------------------------
#     # RESTART
#     # ----------------------------------

#     if not session.is_analysis_done:
#         session.start_analysis()
#         run_analysis_task.delay(session.id)
#     else:
#         session.start_generation()
#         run_generation_task.delay(session.id)

#     return Response({
#         "message": "Retry started",
#         "status": session.status
#     })
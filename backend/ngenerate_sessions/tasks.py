# ngenerate_sessions/tasks.py

from celery import shared_task
from django.db import transaction

from .models import Session
from .services.analysis_workflow import AnalysisWorkflow
# from services.generation_workflow import GenerationWorkflow

from notifications.models import Notification  


# =====================================================
# ANALYSIS TASK
# =====================================================

@shared_task(bind=True, max_retries=0)
def run_analysis_task(self, session_id, notification_id):
    
    session = None
    notification = None

    try:
        session = Session.objects.select_related("novel__user").get(id=session_id)

        notification = Notification.objects.get(id=notification_id)

        workflow = AnalysisWorkflow(session)
        workflow.run()

        session.refresh_from_db()

        if session.status == "analyzed":
            notification.status = "success"
            notification.message = f"Analysis completed successfully for '{session.name}'."
            notification.save(update_fields=["status", "message", "updated_at"])

    except Exception as e:

        if session:
            try:
                session.fail(str(e))
            except:
                pass

        if notification:
            notification.status = "error"
            notification.message = f"Analysis failed: {str(e)}"
            notification.save(update_fields=["status", "message", "updated_at"])
        else:
            if session:
                Notification.objects.create(
                    user=session.novel.user,
                    session=session,
                    task_name="Analysis",
                    status="error",
                    message=f"Analysis failed: {str(e)}"
                )

        raise


# =====================================================
# GENERATION TASK
# =====================================================

# @shared_task(bind=True, max_retries=0)
# def run_generation_task(self, session_id):

#     session = None
#     notification = None

#     try:
#         session = Session.objects.select_related("novel__user").get(id=session_id)

#         notification = Notification.objects.create(
#             user=session.novel.user,
#             session=session,
#             task_name="Generation",
#             status="processing",
#             message=f"Generation started for session '{session.name}'."
#         )

#         workflow = GenerationWorkflow(session)
#         workflow.run()

#         session.refresh_from_db()

#         if session.status == "generated":
#             notification.status = "success"
#             notification.message = f"Generation completed successfully for '{session.name}'."
#             notification.save(update_fields=["status", "message", "updated_at"])

#     except Exception as e:

#         if session:
#             try:
#                 session.fail(str(e))
#             except:
#                 pass

#         if notification:
#             notification.status = "error"
#             notification.message = f"Generation failed: {str(e)}"
#             notification.save(update_fields=["status", "message", "updated_at"])
#         else:
#             if session:
#                 Notification.objects.create(
#                     user=session.novel.user,
#                     session=session,
#                     task_name="Generation",
#                     status="error",
#                     message=f"Generation failed: {str(e)}"
#                 )

#         raise
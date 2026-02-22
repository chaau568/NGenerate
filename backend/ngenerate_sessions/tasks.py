# ngenerate_sessions/tasks.py

from celery import shared_task
from django.db import transaction

from .models import Session
from .services.analysis_workflow import AnalysisWorkflow
from .services.generation_workflow import GenerationWorkflow

# =====================================================
# ANALYSIS TASK
# =====================================================

@shared_task(bind=True, max_retries=0)
def run_analysis_task(self, session_id):
    
    session = None

    try:
        session = Session.objects.select_related("novel__user").get(id=session_id)

        workflow = AnalysisWorkflow(session)
        workflow.run()

        session.refresh_from_db()

    except Exception as e:

        if session:
            try:
                session.fail(str(e))
            except:
                pass

        raise


# =====================================================
# GENERATION TASK
# =====================================================

@shared_task(bind=True, max_retries=0)
def run_generation_task(self, session_id):

    session = None

    try:
        session = Session.objects.select_related("novel__user").get(id=session_id)

        workflow = GenerationWorkflow(session)
        workflow.run()

        session.refresh_from_db()

    except Exception as e:

        if session:
            try:
                session.fail(str(e))
            except:
                pass

        raise
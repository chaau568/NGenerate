import logging

from celery import shared_task
from ngenerate.utils.redis_lock import acquire_lock, release_lock
from django.db import close_old_connections

from .models import Session, GenerationRun
from .services.analysis_workflow import AnalysisWorkflow
from .services.generation_workflow import GenerationWorkflow

logger = logging.getLogger(__name__)


# =====================================================
# ANALYSIS TASK
# =====================================================


@shared_task(bind=True, queue="analysis_queue")
def run_analysis_task(self, session_id):

    lock_key = f"analysis_lock_{session_id}"

    if not acquire_lock(lock_key):
        logger.warning(f"Analysis already running | session={session_id}")
        return

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
            except Exception:
                pass
        raise

    finally:
        release_lock(lock_key)


# =====================================================
# GENERATION TASK
# =====================================================


@shared_task(bind=True, queue="generation_queue")
def run_generation_task(self, generation_run_id):

    lock_key = f"generation_lock_{generation_run_id}"

    if not acquire_lock(lock_key):
        logger.warning(f"Generation already running | run={generation_run_id}")
        return

    run = None

    try:
        run = GenerationRun.objects.select_related("session__novel__user").get(
            id=generation_run_id
        )

        if run.status != "generating":
            logger.warning(
                f"Skip generation | run={generation_run_id} status={run.status}"
            )
            return

        workflow = GenerationWorkflow(run)
        workflow.run_workflow()

    except Exception as e:
        if run:
            close_old_connections()
            try:
                run.fail(str(e))
            except Exception:
                logger.exception(
                    f"Failed to mark generation run failed | run={generation_run_id}"
                )
        raise

    finally:
        release_lock(lock_key)

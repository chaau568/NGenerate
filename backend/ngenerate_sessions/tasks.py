import logging

from celery import shared_task
from ngenerate.utils.redis_lock import acquire_lock, release_lock

from .models import Session
from .services.analysis_workflow import AnalysisWorkflow
from .services.generation_workflow import GenerationWorkflow

from ngenerate_sessions.models import Session

logger = logging.getLogger(__name__)

# =====================================================
# ANALYSIS TASK
# =====================================================


@shared_task(bind=True, queue="analysis")
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
            except:
                pass

        raise

    finally:
        release_lock(lock_key)


# =====================================================
# GENERATION TASK
# =====================================================


@shared_task(bind=True, queue="generation")
def run_generation_task(self, session_id):

    lock_key = f"generation_lock_{session_id}"

    if not acquire_lock(lock_key):
        logger.warning(f"Generation already running | session={session_id}")
        return

    session = None

    try:

        session = Session.objects.get(id=session_id)

        if session.status != "generating":
            logger.warning(
                f"Skip generation | session={session_id} status={session.status}"
            )
            return

        workflow = GenerationWorkflow(session)
        workflow.run()

    except Exception as e:

        if session:
            session.fail(str(e))

        raise

    finally:
        release_lock(lock_key)

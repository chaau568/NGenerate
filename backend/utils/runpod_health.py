import time
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def wait_for_runpod_ready(required=("comfyui", "tts"), timeout=300, interval=15):
    url = f"{settings.AI_API_URL}/health"
    start = time.time()

    while time.time() - start < timeout:
        try:
            res = requests.get(url, timeout=5)
            if res.status_code == 200:
                services = res.json().get("services", {})
                not_ready = [s for s in required if not services.get(s)]
                if not not_ready:
                    logger.info("RunPod all services ready")
                    return True
                logger.info(f"Waiting for services: {not_ready}")
        except Exception as e:
            logger.info(f"RunPod not reachable: {e}")

        time.sleep(interval)

    raise Exception(f"RunPod services not ready after {timeout}s")

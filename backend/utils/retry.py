# utils/retry.py
import time
import logging

logger = logging.getLogger(__name__)


def retry(func, retries=5, delay=15, backoff=2):
    current_delay = delay
    for attempt in range(1, retries + 1):
        try:
            return func()
        except Exception as e:
            logger.warning(f"Retry {attempt}/{retries} failed: {e}")
            if attempt == retries:
                raise
            logger.info(f"Waiting {current_delay}s before retry...")
            time.sleep(current_delay)
            current_delay *= backoff

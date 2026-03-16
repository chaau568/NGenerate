import time
import logging

logger = logging.getLogger(__name__)


def retry(func, retries=3, delay=3):

    for attempt in range(1, retries + 1):

        try:
            return func()

        except Exception as e:

            logger.warning(f"Retry {attempt}/{retries} failed: {e}")

            if attempt == retries:
                raise

            time.sleep(delay)

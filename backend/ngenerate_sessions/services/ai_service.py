import os
import logging
import requests
from django.conf import settings

from .tts_service import TTSService
from .image_service import ImageService
from utils.retry import retry
from utils.runpod_storage import list_runpod_files
import time

logger = logging.getLogger(__name__)


class AIService:

    def __init__(self):
        self.tts = TTSService()
        self.image = ImageService()
        self.BASE_URL = settings.AI_API_URL

    # ===============================
    # VOICE
    # ===============================

    def generate_voice_with_emotion(
        self, text, voice_type, emotion, output_path, **kwargs
    ):

        logger.info(f"TTS | {voice_type} | {emotion} | extra_params={kwargs}")

        return self.tts.generate(
            text=text,
            voice_type=voice_type,
            emotion=emotion,
            output_path=output_path,
            **kwargs,
        )

    # ===============================
    # CHARACTER IMAGE
    # ===============================

    def generate_character_master(self, character_profile, output_path, style="ghibli"):

        return self.image.generate_character_text2image(
            positive_prompt=character_profile.positive_prompt,
            negative_prompt=character_profile.negative_prompt,
            output_path=output_path,
            style=style,
        )

    def generate_character_scene(
        self,
        scene_character,
        reference_image_path,
        output_path,
        style="ghibli",
    ):
        return self.image.generate_character_with_ref(
            positive_prompt=scene_character.positive_prompt,
            negative_prompt=scene_character.negative_prompt,
            reference_image_path=reference_image_path,
            output_path=output_path,
            style=style,
        )

    # ===============================
    # SCENE
    # ===============================

    def generate_scene_image(self, illustration, output_path, style="ghibli"):

        return self.image.generate_scene(
            positive_prompt=illustration.positive_prompt,
            negative_prompt=illustration.negative_prompt,
            width=1280,
            height=720,
            output_path=output_path,
            style=style,
        )

    # ===============================
    # GENERATE VIDEO
    # ===============================

    def start_video_compose(self, timeline, output_path):

        payload = {"timeline": timeline, "output_path": output_path}

        res = requests.post(f"{self.BASE_URL}/video/compose", json=payload, timeout=10)

        res.raise_for_status()

        job_id = res.json()["job_id"]

        return job_id

    def wait_for_video(self, job_id, timeout=7200):
        start = time.time()
        consecutive_errors = 0
        MAX_CONSECUTIVE_ERRORS = 5

        while True:
            try:
                res = requests.get(
                    f"{self.BASE_URL}/video/status/{job_id}",
                    timeout=60,
                )
                consecutive_errors = 0
                res.raise_for_status()
                data = res.json()
                status = data.get("status")

                if status == "completed":
                    return data["video_path"], data["duration"]
                if status == "failed":
                    raise Exception(data.get("error"))

            except requests.exceptions.ReadTimeout as e:
                consecutive_errors += 1
                logger.warning(
                    f"Video status timeout ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}) | job={job_id}"
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    raise Exception(
                        f"Video status endpoint unresponsive after {MAX_CONSECUTIVE_ERRORS} retries"
                    ) from e

            except requests.exceptions.ConnectionError as e:
                consecutive_errors += 1
                logger.warning(
                    f"Video status connection error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS})"
                )
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    raise

            if time.time() - start > timeout:
                raise Exception("Video render timeout")

            logger.info("Waiting video render...")
            time.sleep(60)

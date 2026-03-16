import os
import requests
from django.conf import settings
from utils.retry import retry


class TTSService:

    BASE_URL = settings.AI_API_URL
    TIMEOUT = settings.AI_TIMEOUT
    MASTER_VOICE_DIR = settings.MASTER_VOICE_ROOT

    def generate(
        self,
        text,
        voice_type,
        emotion,
        output_path,
        speed=1.0,
        cfg=2.0,
        step=48,
        cross_fade_duration=0.15,
    ):

        output_path = output_path.replace("\\", "/")
        if output_path.startswith(settings.STORAGE_ROOT):
            output_path = output_path.replace(settings.STORAGE_ROOT + "/", "")

        payload = {
            "voice_type": voice_type,
            "emotion": emotion,
            "text": text,
            "output": output_path,
            "speed": speed,
            "cfg": cfg,
            "step": step,
            "cross_fade_duration": cross_fade_duration,
        }

        def request():

            res = requests.post(
                f"{self.BASE_URL}/tts/generate",
                json=payload,
                timeout=self.TIMEOUT,
            )

            res.raise_for_status()

            data = res.json()

            return data["voice_path"], data["duration"]

        return retry(request, retries=3, delay=3)

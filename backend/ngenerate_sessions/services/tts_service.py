import requests
from django.conf import settings


class TTSService:

    def __init__(self):
        self.base_url = settings.TTS_SERVICE_URL

    def generate(self, text: str, voice_key: str):

        payload = {
            "text": text,
            "voice": voice_key
        }

        response = requests.post(
            f"{self.base_url}/generate",
            json=payload,
            timeout=300
        )

        response.raise_for_status()

        return response.json()
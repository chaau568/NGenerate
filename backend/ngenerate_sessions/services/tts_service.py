import requests
import base64
from pathlib import Path
from django.conf import settings
from django.core.files.base import ContentFile


class TTSService:

    def __init__(self):
        self.base_url = settings.TTS_SERVICE_URL
        self.voice_root = Path(settings.MASTER_VOICE_ROOT)

    def generate(self, text: str, voice_type: str, emotion: str):

        emotion = emotion or "neutral"

        voice_dir = self.voice_root / voice_type

        ref_audio = voice_dir / f"{emotion}.wav"
        ref_text = voice_dir / f"{emotion}.txt"

        if not ref_audio.exists():
            raise FileNotFoundError(f"Voice audio not found: {ref_audio}")

        payload = {
            "ref_audio": str(ref_audio),
            "ref_text": str(ref_text),
            "text": text,
        }

        response = requests.post(
            f"{self.base_url}/generate",
            json=payload,
            timeout=settings.LLAMA_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        audio_bytes = base64.b64decode(data["audio_base64"])

        audio_file = ContentFile(audio_bytes, name="voice.wav")

        return audio_file, data["duration"]

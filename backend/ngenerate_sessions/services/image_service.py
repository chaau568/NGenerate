import requests

from django.conf import settings
from utils.retry import retry
from ngenerate_sessions.services.lora_config import get_lora_config


class ImageService:

    BASE_URL = settings.AI_API_URL
    TIMEOUT = settings.AI_TIMEOUT

    # STYLE ถูกลบออก — style tags อยู่ใน positive_prompt ที่ generate_scene_prompt สร้างมาแล้ว
    # การใส่ซ้ำทำให้ prompt มี "anime style, anime style, ..." และ weight ของ tag อื่นลดลง

    def _post(self, endpoint, payload):
        def request():
            res = requests.post(
                f"{self.BASE_URL}{endpoint}",
                json=payload,
                timeout=self.TIMEOUT,
            )
            res.raise_for_status()
            data = res.json()
            if "image_path" not in data:
                raise Exception("AI API returned invalid response")
            return data["image_path"]

        return retry(request, retries=3, delay=5)

    def _build_lora_payload(self, style: str) -> dict:
        config = get_lora_config(style)
        return {
            "lora_name": config["lora_name"],
            "lora_strength": config["lora_strength"],
        }

    def generate_character_text2image(
        self, positive_prompt, negative_prompt, output_path, style="ghibli"
    ):
        payload = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "output_path": output_path,
            **self._build_lora_payload(style),  # ← inject lora
        }
        return self._post("/generate/character", payload)

    def generate_character_with_ref(
        self,
        positive_prompt,
        negative_prompt,
        reference_image_path,
        output_path,
        style="ghibli",
    ):
        payload = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "reference_image": reference_image_path,
            "output_path": output_path,
            **self._build_lora_payload(style),
        }
        return self._post("/generate/character_ref", payload)

    def generate_scene(
        self,
        positive_prompt,
        negative_prompt,
        width,
        height,
        output_path,
        style="ghibli",
    ):
        payload = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "output_path": output_path,
            **self._build_lora_payload(style),
        }
        return self._post("/generate/scene", payload)

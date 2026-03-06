import requests
import uuid
from django.conf import settings
from django.core.files.base import ContentFile


class ImageService:

    def __init__(self):
        self.base_url = settings.RUNPOD_COMFY_URL
        self.timeout = settings.RUNPOD_TIMEOUT

        self.character_t2i_workflow = settings.CHARACTER_T2I_WORKFLOW_ID
        self.character_ref_workflow = settings.CHARACTER_REF_WORKFLOW_ID
        self.scene_workflow = settings.SCENE_T2I_WORKFLOW_ID

    # =====================================================
    # INTERNAL
    # =====================================================

    def _call_comfy(self, workflow_id, inputs):

        payload = {"workflow_id": workflow_id, "inputs": inputs}

        response = requests.post(
            f"{self.base_url}/run", json=payload, timeout=self.timeout
        )

        response.raise_for_status()

        result = response.json()

        image_url = result["image_url"]

        return self._download_image(image_url)

    def _download_image(self, image_url):

        response = requests.get(image_url, timeout=120)
        response.raise_for_status()

        file_name = f"{uuid.uuid4()}.png"

        return ContentFile(response.content, name=file_name)

    # =====================================================
    # CHARACTER - TEXT TO IMAGE
    # =====================================================

    def generate_character_text2image(
        self, positive_prompt: str, negative_prompt: str = "", style: str = ""
    ):

        inputs = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt or "",
            "style": style,
            "width": 768,
            "height": 1024,
        }

        return self._call_comfy(self.character_t2i_workflow, inputs)

    # =====================================================
    # CHARACTER REF
    # =====================================================

    def generate_character_with_ref(
        self, positive_prompt: str, negative_prompt: str, reference_image_url: str
    ):

        inputs = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt or "",
            "reference_image": reference_image_url,
            "denoise_strength": 0.6,
            "width": 768,
            "height": 1024,
        }

        return self._call_comfy(self.character_ref_workflow, inputs)

    # =====================================================
    # SCENE
    # =====================================================

    def generate_scene(
        self, positive_prompt: str, negative_prompt: str = "", style: str = ""
    ):

        inputs = {
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt or "",
            "style": style,
            "width": 1280,
            "height": 720,
        }

        return self._call_comfy(self.scene_workflow, inputs)

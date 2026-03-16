import requests
from django.conf import settings
from utils.retry import retry


class ImageService:

    BASE_URL = settings.AI_API_URL
    TIMEOUT = settings.AI_TIMEOUT

    STYLE = "anime style, cinematic lighting, high quality"

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

    # --------------------------------------------------

    def generate_character_text2image(
        self,
        positive_prompt,
        negative_prompt,
        output_path,
    ):

        payload = {
            "positive_prompt": f"{positive_prompt}, {self.STYLE}",
            "negative_prompt": negative_prompt,
            "output_path": output_path,
        }

        return self._post("/generate/character", payload)

    # --------------------------------------------------

    def generate_character_with_ref(
        self,
        positive_prompt,
        negative_prompt,
        reference_image_path,
        output_path,
    ):

        payload = {
            "positive_prompt": f"{positive_prompt}, {self.STYLE}",
            "negative_prompt": negative_prompt,
            "reference_image": reference_image_path,
            "output_path": output_path,
        }

        return self._post("/generate/character_ref", payload)

    # --------------------------------------------------

    def generate_scene(
        self,
        positive_prompt,
        negative_prompt,
        width,
        height,
        output_path,
    ):

        payload = {
            "positive_prompt": f"{positive_prompt}, {self.STYLE}",
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "output_path": output_path,
        }

        return self._post("/generate/scene", payload)

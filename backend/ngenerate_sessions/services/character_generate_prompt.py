import json
import re
import requests

from ngenerate_sessions.services.lora_config import get_lora_config


class GenerateCharacterPrompt:
    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

        # framing tags — ไม่เปลี่ยนตาม style
        self.__FRAMING_TAGS = (
            "upper body, bust shot, "
            "full head visible, head fully in frame, "
            "portrait, solo, "
            "looking at viewer, facing viewer, front view, "
            "centered"
        )

        self.__FIXED_SUFFIX = "white background, simple background, isolated"

        # negative — ไม่มี score_6/5/4 เพราะจะ hardcode ไม่ได้
        # score negative ต้องอยู่ใน lora_config เหมือนกัน
        self.__FIXED_NEGATIVE_BASE = (
            "(low quality, worst quality:1.4), "
            "bad anatomy, bad hands, extra fingers, missing fingers, "
            "3d, realistic, photorealistic, "
            "side view, looking away, profile view, "
            "text, watermark, logo, "
            "background scenery, landscape, city, forest, "
            "(cropped head:1.5), (head cut off:1.5), (head out of frame:1.5), "
            "(missing head:1.5), partial head, cut forehead, "
            "close-up face only, headshot without shoulders, "
            "legs, feet, toes, boots, full body, "
            "cowboy shot"
        )

        self.EMOTION_TAGS = {
            "happy": "smiling, bright eyes, cheerful expression",
            "sad": "sad expression, teary eyes, downcast look",
            "angry": "angry expression, furrowed brows, intense eyes",
            "serious": "serious expression, focused gaze, determined look",
            "neutral": "neutral expression, calm face",
        }

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _llm(self, prompt: str, temperature: float = 0.3) -> str:
        payload = {
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }
        response = requests.post(
            f"{self.ai_api_url}/llm/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _extract_json_object(self, text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    def _resolve_identity(self, sex: str, age: str) -> str:
        sex = sex.lower()
        age = age.lower()
        if age == "child":
            return "1baby girl" if sex == "woman" else "1baby boy"
        if age == "teen":
            return "1little girl" if sex == "woman" else "1little boy"
        if age == "adult":
            return "1adult woman" if sex == "woman" else "1adult man"
        if age == "middle-aged":
            return "1middle aged woman" if sex == "woman" else "1middle aged man"
        if age == "elder":
            return "1elderly woman" if sex == "woman" else "1elderly man"
        return "1woman" if sex == "woman" else "1man"

    def _build_prompt_prefix(self, style: str) -> str:
        """
        สร้าง prefix รวม:
          score/quality tags (ต่างกันตาม base model)
          + style tags
          + trigger word (ถ้ามี)
          + framing tags (คงที่)
        """
        config = get_lora_config(style)
        parts = [
            config["score_prefix"],  # "score_9,..." หรือ "best quality,..."
            config["style_tags"],  # style-specific tags
        ]
        if config["trigger_word"]:
            parts.append(config["trigger_word"])  # "stariwei_style" / "guofeng"
        parts.append(self.__FRAMING_TAGS)  # framing คงที่
        return ", ".join(p for p in parts if p)

    def _build_negative(self, style: str) -> str:
        """
        รวม negative base + score negative จาก config
        Pony ต้องการ score_6, score_5, score_4
        SDXL base ไม่ต้องการ
        """
        config = get_lora_config(style)
        score_neg = config.get("score_negative", "")
        if score_neg:
            return f"{score_neg}, {self.__FIXED_NEGATIVE_BASE}"
        return self.__FIXED_NEGATIVE_BASE

    # --------------------------------------------------
    # METHOD 1: APPEARANCE ANCHOR
    # --------------------------------------------------

    def generate_appearance_anchor(
        self,
        character_profile_data: dict,
        style: str,
    ) -> dict:
        sex = character_profile_data.get("sex", "man")
        age = character_profile_data.get("age", "adult")
        identity = self._resolve_identity(sex, age)

        prefix = self._build_prompt_prefix(style)
        negative = self._build_negative(style)

        prompt = f"""You are a Stable Diffusion character design expert.

        Task: Create APPEARANCE ONLY tags for this character.

        Art style: {style}

        STRICT RULES:
        - Describe ONLY: hair color, hair style, eye color, skin tone, face shape, facial features
        - DO NOT include: outfit, clothing, armor, weapons, accessories, pose, expression, background
        - comma separated tags
        - 8 to 14 tags only
        - English only

        Character data:
        {json.dumps(character_profile_data, ensure_ascii=False)}

        Example output:
        {{"appearance_tags": "long black hair, straight hair, large dark brown eyes, fair skin, soft facial features, small nose, gentle face"}}

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.3)
            data = self._extract_json_object(raw)
            appearance_tags = data.get("appearance_tags", "").strip()

            if not appearance_tags:
                raise ValueError("Empty appearance tags")

            full_prompt = (
                f"{prefix}, "
                f"{identity}, "
                f"{appearance_tags}, "
                f"{self.__FIXED_SUFFIX}"
            )

            return {
                "positive_prompt": full_prompt,
                "negative_prompt": negative,
                "_appearance_tags": appearance_tags,
                "_identity": identity,
            }

        except Exception as e:
            print(f"⚠ Appearance anchor error: {e}")
            fallback_tags = "simple character design, neutral appearance"
            return {
                "positive_prompt": (
                    f"{prefix}, "
                    f"{identity}, "
                    f"{fallback_tags}, "
                    f"{self.__FIXED_SUFFIX}"
                ),
                "negative_prompt": negative,
                "_appearance_tags": fallback_tags,
                "_identity": identity,
            }

    # --------------------------------------------------
    # METHOD 2: SCENE-AWARE PROMPT
    # --------------------------------------------------

    def generate_scene_prompt(
        self,
        appearance_anchor: str,
        identity: str,
        scene_description: str,
        character_name: str,
        emotion: str,
        style: str,
    ) -> dict:
        emotion_tags = self.EMOTION_TAGS.get(emotion, self.EMOTION_TAGS["neutral"])
        prefix = self._build_prompt_prefix(style)
        negative = self._build_negative(style)

        prompt = f"""You are a Stable Diffusion character prompt engineer.

        Character: {character_name}
        Scene setting: {scene_description}
        Art style: {style}

        Task: Decide what {character_name} is wearing and doing in this scene.

        Base appearance (DO NOT repeat these in your output):
        {appearance_anchor}

        Output rules:
        - Describe ONLY: outfit, clothing type, accessories WORN, activity/pose
        - Infer clothing from the scene setting and art style
        - DO NOT repeat appearance tags (hair, eyes, skin)
        - comma separated tags
        - 6 to 10 tags only
        - English only

        Example output:
        {{"outfit_tags": "worn cotton shirt, loose trousers, straw hat, barefoot"}}

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.45)
            data = self._extract_json_object(raw)
            outfit_tags = (
                data.get("outfit_tags", "").strip() or "simple casual clothing"
            )

            full_prompt = (
                f"{prefix}, "
                f"{identity}, "
                f"{appearance_anchor}, "
                f"{outfit_tags}, "
                f"{emotion_tags}, "
                f"{self.__FIXED_SUFFIX}"
            )

            return {
                "positive_prompt": full_prompt,
                "negative_prompt": negative,
            }

        except Exception as e:
            print(f"⚠ Scene prompt error [{character_name}|{emotion}]: {e}")
            return {
                "positive_prompt": (
                    f"{prefix}, "
                    f"{identity}, "
                    f"{appearance_anchor}, "
                    f"simple casual clothing, "
                    f"{emotion_tags}, "
                    f"{self.__FIXED_SUFFIX}"
                ),
                "negative_prompt": negative,
            }

    def generate_prompt(self, character_profile_data: dict, style: str) -> dict:
        return self.generate_appearance_anchor(character_profile_data, style)

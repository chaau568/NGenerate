import json
import re
import requests

from ngenerate_sessions.services.lora_config import get_lora_config


class GenerateCharacterPrompt:
    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

        self.__FRAMING_TAGS = (
            "upper body, half body, "
            "solo, looking at viewer, facing viewer, front view, "
            "centered, "
            "head visible, neck visible, shoulders visible, arms visible, hands visible"
        )

        self.__FIXED_SUFFIX = "white background, simple background, isolated"

        self.__FIXED_NEGATIVE_BASE = (
            "(low quality, worst quality:1.4), "
            "bad anatomy, bad hands, extra fingers, missing fingers, "
            "3d, realistic, photorealistic, "
            "side view, looking away, profile view, "
            "text, watermark, logo, "
            "background scenery, landscape, city, forest, "
            "(cropped head:1.5), (head cut off:1.5), (head out of frame:1.5), "
            "(cropped hands:1.3), (hands cut off:1.3), (arms cut off:1.3), "
            "full body, wide shot, feet visible, shoes visible, "
            "out of frame, cropped, cut off"
        )

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
        config = get_lora_config(style)
        parts = [
            config["score_prefix"],
            config["style_tags"],
        ]
        if config["trigger_word"]:
            parts.append(config["trigger_word"])
        parts.append(self.__FRAMING_TAGS)
        return ", ".join(p for p in parts if p)

    def _build_negative(self, style: str) -> str:
        config = get_lora_config(style)
        score_neg = config.get("score_negative", "")
        if score_neg:
            return f"{score_neg}, {self.__FIXED_NEGATIVE_BASE}"
        return self.__FIXED_NEGATIVE_BASE

    def _build_expression_tags(self, sc) -> tuple[str, str]:
        action_parts = []
        emotion_parts = []

        action = sc.get("action", "").strip()
        pose = sc.get("pose", "standing").strip()

        if action and action.lower() not in ["", "none"]:
            action_parts.append(f"(({action}, {pose}):1.4)")
        elif pose:
            action_parts.append(f"({pose}:1.2)")

        if len(action_parts) > 0:
            action_parts.append("(upper body:1.3), (half body:1.2), hands visible")

        # ── Expression ──
        expr = sc.get("expression", "neutral").strip()
        if expr.lower() not in ("", "none", "neutral"):
            emotion_parts.append(f"{expr} expression")

        action_tags = ", ".join(action_parts) if action_parts else "standing"
        emotion_tags = ", ".join(emotion_parts) if emotion_parts else ""
        return action_tags, emotion_tags

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
        scene_character,
        style: str,
    ) -> dict:
        action_tags, emotion_tags = self._build_expression_tags(scene_character)
        prefix = self._build_prompt_prefix(style)
        negative = self._build_negative(style)

        action_raw = scene_character.get("action", "").strip()
        pose_raw = scene_character.get("pose", "standing").strip()
        expr_raw = scene_character.get("expression", "neutral").strip()

        # ─── บอก LLM ให้รู้ว่าตัวละครกำลังทำอะไร และต้องการอะไรใน outfit ───
        weapon_hint = ""
        weapon_keywords = [
            "sword",
            "spear",
            "bow",
            "arrow",
            "staff",
            "blade",
            "dagger",
            "lance",
            "axe",
            "weapon",
            "gun",
            "rifle",
            "knife",
            "ทวน",
            "ดาบ",
            "หอก",
            "คันธนู",
            "กระบอง",  # Thai keywords
        ]
        action_lower = action_raw.lower()
        has_weapon = any(kw in action_lower for kw in weapon_keywords)
        if has_weapon:
            weapon_hint = (
                "\n        IMPORTANT: The character is using a weapon in this action. "
                "You MUST describe the weapon's appearance in detail within outfit_tags."
            )

        prompt = f"""You are a Stable Diffusion character prompt engineer.

        Character: {character_name}
        Scene setting: {scene_description}
        Current action: {action_raw if action_raw else 'none'}
        Current pose: {pose_raw}
        Expression: {expr_raw}
        Art style: {style}
        {weapon_hint}

        Task: Decide what {character_name} is wearing and holding that fits their current action and scene.

        Base appearance (DO NOT repeat these): {appearance_anchor}

        Rules:
        - Describe OUTFIT that matches the action and scene atmosphere
        - If the character is doing a physical action (fighting, running, casting spell),
          choose clothes appropriate for that activity
        - If the action involves holding/using an object or weapon, describe it explicitly
          (e.g., "holding a silver spear with red tassel", "gripping ornate sword hilt")
        - DO NOT repeat appearance tags (hair, eyes, skin, face)
        - 6 to 12 tags only, comma separated, English only

        Example (fighting scene):
        {{"outfit_tags": "warrior training robe, leather bracers, silver spear with red tassel, combat stance"}}

        Example (calm scene):
        {{"outfit_tags": "light blue hanfu, jade hair ornament, flowing sleeves, relaxed posture"}}

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.45)
            data = self._extract_json_object(raw)
            outfit_tags = (
                data.get("outfit_tags", "").strip() or "simple casual clothing"
            )

            # ── ประกอบ final prompt ──
            # ลำดับสำคัญ: prefix → identity → appearance → outfit/weapon → action → emotion → suffix
            parts = [
                "upper body, half body, hands visible,",
                prefix,
                identity,
                appearance_anchor,
                outfit_tags,
                action_tags,
            ]
            if emotion_tags:
                parts.append(emotion_tags)
            parts.append(self.__FIXED_SUFFIX)

            full_prompt = ", ".join(p for p in parts if p)

            return {
                "positive_prompt": full_prompt,
                "negative_prompt": negative,
            }

        except Exception as e:
            print(f"⚠ Scene prompt error [{character_name}]: {e}")
            action_tags_fb, emotion_tags_fb = self._build_expression_tags(
                scene_character
            )
            parts = [
                prefix,
                identity,
                appearance_anchor,
                "simple casual clothing",
                action_tags_fb,
            ]
            if emotion_tags_fb:
                parts.append(emotion_tags_fb)
            parts.append(self.__FIXED_SUFFIX)
            return {
                "positive_prompt": ", ".join(p for p in parts if p),
                "negative_prompt": negative,
            }

    def generate_prompt(self, character_profile_data: dict, style: str) -> dict:
        return self.generate_appearance_anchor(character_profile_data, style)

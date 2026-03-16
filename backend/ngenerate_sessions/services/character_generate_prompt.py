import json
import requests


class GenerateCharacterPrompt:

    def __init__(self, ai_api_url: str, timeout: int):

        self.ai_api_url = ai_api_url
        self.timeout = timeout

        # Pony SDXL prefix
        self.__PROMPT_PREFIX = (
            "score_9, score_8_up, score_7_up, "
            "source_anime, anime style, "
            "portrait, upper body, from head to waist, solo, "
            "looking at viewer, facing viewer, front view"
        )

        self.__FIXED_SUFFIX = "white background, simple background, isolated"

        self.__FIXED_CHAR_NEGATIVE = (
            "score_6, score_5, score_4, "
            "(low quality, worst quality:1.4), "
            "bad anatomy, bad hands, extra fingers, missing fingers, "
            "3d, realistic, photorealistic, "
            "side view, looking away, profile view, "
            "text, watermark, logo, "
            "background scenery, landscape, city, forest, "
            "weapon, sword, gun, "
            "legs, feet, toes, boots, pants, full body, lower body"
        )

    # ------------------------------------------------
    # AGE → PROMPT IDENTITY
    # ------------------------------------------------

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

    # ------------------------------------------------

    def generate_prompt(self, character_profile_data: dict, style: str) -> dict:

        sex = character_profile_data.get("sex", "man")
        age = character_profile_data.get("age", "adult")

        identity = self._resolve_identity(sex, age)

        prompt = f"""
        You are an expert Stable Diffusion prompt engineer specialized in Pony SDXL anime models.

        Your task is to create high quality tag prompts for an anime character portrait.

        STRICT RULES:
        - comma separated tags
        - DO NOT include character name
        - DO NOT include Thai or English names
        - NO sentences
        - NO explanations
        - portrait composition
        - upper body only
        - from head to waist
        - character MUST face forward
        - looking at viewer
        - front view
        - NO side view
        - NO background scenery

        IMPORTANT OUTFIT RULES:

        Outfit MUST follow the character_profile_data.

        If outfit is:
        - "not described"
        - "simple casual clothing"

        Then generate normal casual clothing only.

        DO NOT invent:
        - armor
        - knight armor
        - battle armor
        - fantasy armor
        - weapons

        Character data:
        {json.dumps(character_profile_data)}

        Style theme:
        {style}

        Return JSON only.

        Example:

        {{
        "positive_prompt": "short black hair, bright eyes, gentle smile, simple shirt, casual clothing, anime style, soft lighting"
        }}
        """

        payload = {
            "prompt": prompt,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }

        try:

            response = requests.post(
                f"{self.ai_api_url}/llm/generate",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            text = response.json()["response"].strip()

            if "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].replace("json", "").strip()

            start = text.find("{")
            end = text.rfind("}")

            if start != -1 and end != -1:
                text = text[start : end + 1]

            raw = json.loads(text)

            cleaned = raw.get("positive_prompt", "").strip()

            final_prompt = (
                f"{self.__PROMPT_PREFIX}, "
                f"{identity}, "
                f"{cleaned}, "
                f"{self.__FIXED_SUFFIX}"
            )

            return {
                "positive_prompt": final_prompt,
                "negative_prompt": self.__FIXED_CHAR_NEGATIVE,
            }

        except Exception as e:

            print(f"❌ Character Prompt API Error: {e}")

            fallback = (
                f"{self.__PROMPT_PREFIX}, "
                f"{identity}, "
                "simple anime character design, neutral expression, anime fantasy style, "
                f"{self.__FIXED_SUFFIX}"
            )

            return {
                "positive_prompt": fallback,
                "negative_prompt": self.__FIXED_CHAR_NEGATIVE,
            }

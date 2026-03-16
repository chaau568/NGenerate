import json
import requests
from typing import Dict, Optional


class SceneAnalysis:

    def __init__(self, ai_api_url: str, timeout: int):

        self.ai_api_url = ai_api_url
        self.timeout = timeout

        self.__PROMPT_PREFIX = (
            "score_9, score_8_up, score_7_up, "
            "source_anime, scenery, anime_background, "
            "eye level view, wide shot"
        )

        self.__FIXED_NEGATIVE_PROMPT = (
            "score_6, score_5, score_4, "
            "(low quality, worst quality:1.4), "
            "human, people, person, man, woman, boy, girl, character, "
            "text, watermark, logo, 3d, realistic"
        )

        # tags ที่ห้าม LLM spam
        self.__BANNED_GENERIC = {
            "beautiful landscape",
            "fantasy scenery",
            "serene atmosphere",
            "peaceful landscape",
            "detailed environment",
            "epic scenery",
        }

    # ------------------------------------------------
    # Extract context
    # ------------------------------------------------

    def _extract_scene_context(self, text: str) -> str:

        if len(text) < 3000:
            return text

        start = text[:1200]
        middle = text[len(text) // 2 - 500 : len(text) // 2 + 500]
        end = text[-1200:]

        return f"{start}\n...\n{middle}\n...\n{end}"

    # ------------------------------------------------
    # Remove duplicates and generic tags
    # ------------------------------------------------

    def _clean_tags(self, text: str) -> str:

        banned_tags = {
            "score_9",
            "score_8_up",
            "score_7_up",
            "source_anime",
            "scenery",
            "anime_background",
            "eye level view",
            "wide shot",
        }

        tags = [t.strip().lower() for t in text.split(",") if t.strip()]

        clean = []

        for tag in tags:

            if tag in banned_tags:
                continue

            if tag in self.__BANNED_GENERIC:
                continue

            if tag not in clean:
                clean.append(tag)

        return ", ".join(clean[:35])

    # ------------------------------------------------
    # Main analysis
    # ------------------------------------------------

    def analyze_master_scene(self, chapter_text: str, style: str) -> Optional[Dict]:

        allowed_style = {
            "chinese",
            "japanese",
            "futuristic",
            "medieval",
            "modern",
            "ghibli",
        }

        style = (style or "").lower()

        if style not in allowed_style:
            style = "ghibli"

        scene_context = self._extract_scene_context(chapter_text)

        prompt = f"""
        You are an expert Stable Diffusion background prompt engineer specialized in Pony SDXL anime models.

        Goal:
        Generate a UNIQUE anime background prompt describing the main environment of this chapter.

        Important rules:

        - scenery only
        - no humans
        - no characters
        - comma separated tags
        - 25 to 35 tags
        - no full sentences
        - tags must be visual objects or environment features

        Avoid generic fantasy templates like:
        "beautiful landscape", "fantasy scenery", "serene atmosphere".

        Focus on elements such as:

        environment
        architecture
        terrain
        vegetation
        weather
        lighting
        time of day
        atmosphere
        important environmental objects

        The scene MUST be specific to the story context.

        Style theme:
        {style}

        Story excerpt:
        {scene_context}

        Return JSON only.

        Example:

        {{
        "positive_prompt": "ancient stone bridge, narrow river, moss covered rocks, bamboo forest, misty valley, wooden shrine, paper lanterns, soft fog, morning sunlight"
        }}
        """

        payload = {
            "prompt": prompt,
            "options": {
                "temperature": 0.7,
                "top_p": 0.95,
                "repeat_penalty": 1.2,
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

            data = json.loads(text)

            cleaned = self._clean_tags(data["positive_prompt"])

            final_prompt = f"{self.__PROMPT_PREFIX}, {cleaned}"

            return {
                "positive_prompt": final_prompt,
                "negative_prompt": self.__FIXED_NEGATIVE_PROMPT,
            }

        except Exception as e:

            print(f"Scene analysis error: {e}")

            fallback = (
                f"{self.__PROMPT_PREFIX}, "
                "lush forest valley, misty mountains, stone path, cinematic lighting"
            )

            return {
                "positive_prompt": fallback,
                "negative_prompt": self.__FIXED_NEGATIVE_PROMPT,
            }

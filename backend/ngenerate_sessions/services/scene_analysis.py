# ngenerate_sessions/services/scene_analysis.py
import json
import re
import requests
from typing import Dict, List, Optional

from ngenerate_sessions.services.lora_config import get_lora_config


class SceneAnalysis:

    MAX_SCENES_PER_CHAPTER = 5
    MIN_SENTENCES_PER_SCENE = 3

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

        # framing tags สำหรับ scene — คงที่ทุก style
        self.__SCENE_FRAMING = "scenery, anime_background, eye level view, wide shot"

        # negative base — ไม่มี score tags (จะเติมจาก config)
        self.__FIXED_NEGATIVE_BASE = (
            "(low quality, worst quality:1.4), "
            "human, people, person, man, woman, boy, girl, character, "
            "text, watermark, logo, 3d, realistic"
        )

        self.__BANNED_TAGS = {
            "beautiful landscape",
            "fantasy scenery",
            "serene atmosphere",
            "peaceful landscape",
            "detailed environment",
            "epic scenery",
            # กัน LLM ใส่ prefix tags ซ้ำใน content
            "score_9",
            "score_8_up",
            "score_7_up",
            "source_anime",
            "scenery",
            "anime_background",
            "eye level view",
            "wide shot",
        }

    # --------------------------------------------------
    # HELPERS
    # --------------------------------------------------

    def _llm(self, prompt: str, temperature: float = 0.5) -> str:
        payload = {
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "top_p": 0.95,
                "repeat_penalty": 1.2,
            },
        }
        response = requests.post(
            f"{self.ai_api_url}/llm/generate",
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _extract_json_array(self, text: str) -> list:
        text = re.sub(r"```(?:json)?", "", text).strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

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

    def _clean_tags(self, text: str) -> str:
        tags = [t.strip().lower() for t in text.split(",") if t.strip()]
        clean = []
        for tag in tags:
            if tag in self.__BANNED_TAGS:
                continue
            if tag not in clean:
                clean.append(tag)
        return ", ".join(clean[:35])

    def _build_scene_prefix(self, style: str) -> str:
        """
        score/quality tags + style tags + trigger word + scene framing
        แยกตาม base model เหมือน character prompt
        """
        config = get_lora_config(style)
        parts = [
            config["score_prefix"],  # "score_9,..." หรือ "best quality,..."
            self.__SCENE_FRAMING,  # คงที่
            config["style_tags"],  # style-specific tags
        ]
        if config["trigger_word"]:
            parts.append(config["trigger_word"])
        return ", ".join(p for p in parts if p)

    def _build_negative(self, style: str) -> str:
        """
        score negative (ถ้ามี) + negative base
        """
        config = get_lora_config(style)
        score_neg = config.get("score_negative", "")
        if score_neg:
            return f"{score_neg}, {self.__FIXED_NEGATIVE_BASE}"
        return self.__FIXED_NEGATIVE_BASE

    def _fallback_prompt(self, style: str) -> dict:
        fallback_map = {
            "ghibli": "lush green valley, rural village, wooden houses, misty hills, morning light",
            "chinese": "ancient courtyard, red pillars, stone lanterns, bamboo grove, misty mountains",
            "chinese-modern": "xianxia mountain peak, ancient chinese palace, cherry blossoms, golden light, dramatic clouds",
            "fantasy": "enchanted forest, glowing mushrooms, stone ruins, magical light rays, ancient trees",
            "medieval": "stone castle walls, cobblestone road, torch light, cloudy sky, old wooden gate",
            "futuristic": "neon lit city, glass towers, rain puddles, holographic signs, night time",
        }
        scene_tags = fallback_map.get(style, fallback_map["ghibli"])
        prefix = self._build_scene_prefix(style)
        return {
            "positive_prompt": f"{prefix}, {scene_tags}",
            "negative_prompt": self._build_negative(style),
        }

    # --------------------------------------------------
    # STEP 1: DETECT SCENE BOUNDARIES — ไม่เปลี่ยน logic
    # --------------------------------------------------

    def _detect_scene_boundaries(self, sentences: List[Dict], style: str) -> List[Dict]:
        lines = []
        for s in sentences:
            short_text = s["text"][:80].replace("\n", " ")
            lines.append(f'{s["sentence_index"]}: {short_text}')

        sentence_block = "\n".join(lines)
        first_idx = sentences[0]["sentence_index"]
        last_idx = sentences[-1]["sentence_index"]

        prompt = f"""You are a story scene director.

        Split the story sentences below into {self.MAX_SCENES_PER_CHAPTER} scenes or fewer.

        Rules:
        - Each scene must cover a continuous range of sentences
        - Scenes change when: location changes, time passes, mood shifts significantly
        - Minimum {self.MIN_SENTENCES_PER_SCENE} sentences per scene
        - sentence_start and sentence_end must be actual sentence indexes from the list
        - Cover ALL sentences: first={first_idx}, last={last_idx}
        - scene_description: 1 short English phrase describing the environment/setting

        Example output:
        [
        {{"scene_index": 1, "sentence_start": 1, "sentence_end": 12, "scene_description": "morning rice field, village path"}},
        {{"scene_index": 2, "sentence_start": 13, "sentence_end": 25, "scene_description": "riverside at sunset, bamboo huts"}}
        ]

        Sentences:
        {sentence_block}

        Return JSON array only:"""

        try:
            raw = self._llm(prompt, temperature=0.4)
            scenes = self._extract_json_array(raw)
            return self._validate_scene_boundaries(scenes, first_idx, last_idx)
        except Exception as e:
            print(f"⚠ Scene boundary detection error: {e}")
            return [
                {
                    "scene_index": 1,
                    "sentence_start": first_idx,
                    "sentence_end": last_idx,
                    "scene_description": "story scene",
                }
            ]

    def _validate_scene_boundaries(
        self, scenes: list, first_idx: int, last_idx: int
    ) -> List[Dict]:
        # ไม่เปลี่ยน logic เลย
        if not scenes:
            return [
                {
                    "scene_index": 1,
                    "sentence_start": first_idx,
                    "sentence_end": last_idx,
                    "scene_description": "story scene",
                }
            ]

        try:
            scenes = sorted(scenes, key=lambda x: x.get("sentence_start", 0))
        except Exception:
            pass

        valid = []
        for i, scene in enumerate(scenes):
            try:
                s_start = int(scene["sentence_start"])
                s_end = int(scene["sentence_end"])
                desc = str(scene.get("scene_description", "")).strip() or "story scene"
                if s_start > s_end or s_start < first_idx or s_end > last_idx:
                    continue
                valid.append(
                    {
                        "scene_index": i + 1,
                        "sentence_start": s_start,
                        "sentence_end": s_end,
                        "scene_description": desc,
                    }
                )
            except (KeyError, ValueError, TypeError):
                continue

        if not valid:
            return [
                {
                    "scene_index": 1,
                    "sentence_start": first_idx,
                    "sentence_end": last_idx,
                    "scene_description": "story scene",
                }
            ]

        valid[0]["sentence_start"] = first_idx
        valid[-1]["sentence_end"] = last_idx
        for i, scene in enumerate(valid):
            scene["scene_index"] = i + 1
        return valid

    # --------------------------------------------------
    # STEP 2: GENERATE PROMPT FOR EACH SCENE
    # --------------------------------------------------

    def _generate_scene_prompt(
        self, scene_description: str, scene_text: str, style: str
    ) -> Dict:
        if len(scene_text) > 2000:
            scene_text = scene_text[:2000] + "..."

        prefix = self._build_scene_prefix(style)
        negative = self._build_negative(style)

        prompt = f"""You are a Stable Diffusion background prompt engineer.

        Create a background/scenery prompt for this scene.

        Scene setting: {scene_description}
        Art style: {style}

        Rules:
        - scenery only, NO humans or characters
        - comma separated tags
        - 20 to 30 specific tags
        - describe environment, architecture, lighting, time of day, weather
        - NO generic tags like "beautiful landscape" or "fantasy scenery"
        - tags must be concrete visual elements

        Story excerpt:
        \"\"\"{scene_text}\"\"\"

        Example output:
        {{"positive_prompt": "stone bridge, narrow canal, weeping willow, lanterns reflected in water, evening glow, wooden boats"}}

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.7)
            data = self._extract_json_object(raw)
            raw_tags = data.get("positive_prompt", "")
            cleaned = self._clean_tags(raw_tags)

            if not cleaned:
                raise ValueError("Empty prompt")

            return {
                "positive_prompt": f"{prefix}, {cleaned}",
                "negative_prompt": negative,
            }

        except Exception as e:
            print(f"⚠ Scene prompt error: {e}")
            return self._fallback_prompt(style)

    # --------------------------------------------------
    # PUBLIC ENTRY POINT — ไม่เปลี่ยน
    # --------------------------------------------------

    def analyze_chapter_scenes(
        self, chapter_text: str, sentences: List[Dict], style: str
    ) -> List[Dict]:
        if not sentences:
            return [
                {
                    "scene_index": 1,
                    "sentence_start": 0,
                    "sentence_end": 0,
                    "scene_description": "story scene",
                    **self._fallback_prompt(style),
                }
            ]

        print(f"🎬 Detecting scene boundaries ({len(sentences)} sentences)...")
        scene_boundaries = self._detect_scene_boundaries(sentences, style)
        print(f"   → {len(scene_boundaries)} scenes detected")

        sent_map = {s["sentence_index"]: s["text"] for s in sentences}
        results = []

        for scene in scene_boundaries:
            s_start = scene["sentence_start"]
            s_end = scene["sentence_end"]
            desc = scene["scene_description"]

            scene_sentences = [
                sent_map[idx] for idx in range(s_start, s_end + 1) if idx in sent_map
            ]
            scene_text = " ".join(scene_sentences)

            print(
                f"   🖼 Scene {scene['scene_index']}: sentences {s_start}-{s_end} | {desc}"
            )
            prompt_data = self._generate_scene_prompt(desc, scene_text, style)

            results.append(
                {
                    "scene_index": scene["scene_index"],
                    "sentence_start": s_start,
                    "sentence_end": s_end,
                    "scene_description": desc,
                    **prompt_data,
                }
            )

        return results

    def analyze_master_scene(self, chapter_text: str, style: str) -> Optional[Dict]:
        """Legacy method"""
        from .convert import ConvertTextToJson

        converter = ConvertTextToJson()
        story_json = converter.text_file_to_json(chapter_text)
        sentences = story_json["sentences"]
        results = self.analyze_chapter_scenes(chapter_text, sentences, style)
        if results:
            r = results[0]
            return {
                "positive_prompt": r["positive_prompt"],
                "negative_prompt": r["negative_prompt"],
            }
        return self._fallback_prompt(style)

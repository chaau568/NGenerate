import json
import re
import requests
from typing import Dict, List, Optional, Tuple

from ngenerate_sessions.services.lora_config import get_lora_config


class SceneAnalysis:

    SCENE_CHUNK_SIZE = 20
    MAX_SCENES_PER_CHUNK = 3
    MIN_SENTENCES_PER_SCENE = 5

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

        self.__SCENE_FRAMING = "scenery, anime_background, eye level view, wide shot"
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
            "score_9",
            "score_8_up",
            "score_7_up",
            "source_anime",
            "scenery",
            "anime_background",
            "eye level view",
            "wide shot",
        }

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

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
            f"{self.ai_api_url}/llm/generate", json=payload, timeout=self.timeout
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
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return {}

    def _clean_tags(self, text: str) -> str:
        if not text:
            return ""
        tags = [t.strip() for t in text.replace("\n", " ").split(",") if t.strip()]
        clean = []
        for tag in tags:
            if tag.lower() in self.__BANNED_TAGS:
                continue
            if tag not in clean:
                clean.append(tag[:50])
        return ", ".join(clean[:35])

    def _build_scene_prefix(self, style: str) -> str:
        config = get_lora_config(style)
        parts = [config["score_prefix"], self.__SCENE_FRAMING, config["style_tags"]]
        if config["trigger_word"]:
            parts.append(config["trigger_word"])
        return ", ".join(p for p in parts if p)

    def _build_negative(self, style: str) -> str:
        config = get_lora_config(style)
        score_neg = config.get("score_negative", "")
        return (
            f"{score_neg}, {self.__FIXED_NEGATIVE_BASE}"
            if score_neg
            else self.__FIXED_NEGATIVE_BASE
        )

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

    # ─────────────────────────────────────────────
    # BOUNDARY DETECTION
    # ─────────────────────────────────────────────

    def _detect_scene_boundaries(self, sentences: List[Dict], style: str) -> List[Dict]:
        lines = []
        for s in sentences:
            short_text = s["text"][:100].replace("\n", " ")
            lines.append(f'{s["sentence_index"]}: {short_text}')

        sentence_block = "\n".join(lines)
        first_idx = sentences[0]["sentence_index"]
        last_idx = sentences[-1]["sentence_index"]

        prompt = f"""You are a story scene director reading a Thai novel.

        Split the sentences below into scenes based on what ACTUALLY HAPPENS in the text.

        Rules:
        - A new scene starts when: physical location changes, significant time passes, or the situation/activity changes clearly
        - Minimum {self.MIN_SENTENCES_PER_SCENE} sentences per scene
        - Maximum {self.MAX_SCENES_PER_CHUNK} scenes for this chunk
        - sentence_start and sentence_end must be actual sentence indexes from the list
        - Cover ALL sentences: first={first_idx}, last={last_idx}
        - scene_description: Write a SHORT phrase (under 10 words) describing the ACTUAL LOCATION and ACTIVITY happening in those sentences. Be specific to the story content — do NOT write generic phrases like "story scene" or "village".

        Good scene_description examples:
        "riverbank at night, character falls into water"
        "bamboo forest path, two characters arguing"
        "stone training ground, sword practice"
        "dark cave interior, searching for exit"
        "crowded market street, midday"

        Sentences:
        {sentence_block}

        Return JSON array only:
        [
        {{"scene_index": 1, "sentence_start": {first_idx}, "sentence_end": X, "scene_description": "..."}},
        ...
        ]"""

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

    # ─────────────────────────────────────────────
    # MERGE SCENES
    # ─────────────────────────────────────────────

    def _merge_chunk_scenes(self, all_chunk_scenes: List[List[Dict]]) -> List[Dict]:
        merged: List[Dict] = []
        for chunk_scenes in all_chunk_scenes:
            for scene in chunk_scenes:
                merged.append(
                    {
                        "sentence_start": scene["sentence_start"],
                        "sentence_end": scene["sentence_end"],
                        "scene_description": scene["scene_description"],
                    }
                )

        if not merged:
            return []

        merged.sort(key=lambda x: x["sentence_start"])

        collapsed: List[Dict] = []
        for scene in merged:
            if (
                collapsed
                and collapsed[-1]["scene_description"] == scene["scene_description"]
                and collapsed[-1]["sentence_end"] + 1 == scene["sentence_start"]
            ):
                collapsed[-1]["sentence_end"] = scene["sentence_end"]
            else:
                collapsed.append(dict(scene))

        for i, scene in enumerate(collapsed):
            scene["scene_index"] = i + 1

        return collapsed

    # ─────────────────────────────────────────────
    # BACKGROUND PROMPT GENERATION
    # ─────────────────────────────────────────────

    def _generate_scene_prompt(
        self, scene_description: str, scene_text: str, style: str
    ) -> Dict:
        """
        Generate background-only scene prompt from actual story content.
        Forces LLM to read the text and extract concrete visual elements.
        """
        if len(scene_text) > 2500:
            scene_text = scene_text[:2500] + "..."

        prefix = self._build_scene_prefix(style)
        negative = self._build_negative(style)

        prompt = f"""You are a Stable Diffusion prompt engineer creating a BACKGROUND/SCENERY prompt.
        The image must show ONLY the environment — no characters, no people.

        Art style: {style}
        Scene summary: {scene_description}

        Story text (read this to understand what the environment actually looks like):
        ---
        {scene_text}
        ---

        Your task:
        1. Read the story text and identify the ACTUAL location and environment described.
        2. Extract concrete visual elements: architecture, terrain, objects, lighting, weather, time of day.
        3. If the story describes fighting/chaos → include battle damage, dust, debris, broken objects.
        4. If the story describes night → include darkness, moonlight, shadows, lanterns.
        5. If the story describes rain/storm → include rain streaks, wet surfaces, dark clouds.
        6. Do NOT invent locations not mentioned or implied in the text.
        7. Do NOT use generic atmospheric filler tags like "beautiful", "epic", "serene", "fantasy scenery".
        
        STRICT RULES:
        - NEVER include any humans or human-related words.
        - NEVER include words like: person, people, man, woman, warrior, fighter, figure, silhouette, enemy, soldier.
        - If a scene involves action, describe ONLY the environment AFTER the action (damage, objects, surroundings).
        - The scene must look EMPTY of people.

        Output format: 20-30 comma-separated English visual tags, ordered:
        LOCATION TYPE → ARCHITECTURE/TERRAIN DETAILS → OBJECTS/PROPS → LIGHTING → WEATHER/ATMOSPHERE

        Example (riverside at night, character being attacked):
        stone riverbank, shallow rushing water, large boulders, gnarled tree roots, moonlight reflecting on water, deep shadows between rocks, scattered fallen leaves, cold night air, mist rising from water, ominous atmosphere

        Example (village home interior, medical examination):
        small wooden room interior, straw mat floor, simple wooden furniture, clay medicine jars on shelf, oil lamp casting warm light, paper sliding door, low ceiling beams, herbs hanging to dry, quiet domestic atmosphere

        Now write the tags for this scene.
        Return JSON only: {{"positive_prompt": "tag1, tag2, tag3, ..."}}"""

        try:
            raw = self._llm(prompt, temperature=0.55)
            data = self._extract_json_object(raw)

            if "positive_prompt" in data:
                raw_tags = data["positive_prompt"]
            else:
                raw_tags = raw.strip()
                raw_tags = re.sub(r"```(?:json)?", "", raw_tags).strip()
                json_match = re.search(r'"positive_prompt"\s*:\s*"([^"]+)"', raw_tags)
                raw_tags = json_match.group(1) if json_match else raw_tags

            cleaned = self._clean_tags(raw_tags)

            if len(cleaned.split(",")) < 8 or not cleaned:
                raise ValueError("Too few tags")

            final_prompt = f"{prefix}, {cleaned}"
            if len(final_prompt) > 500:
                final_prompt = final_prompt[:500]

            return {"positive_prompt": final_prompt, "negative_prompt": negative}

        except Exception as e:
            print(f"⚠ Scene prompt error: {e}")
            return self._fallback_prompt(style)

    # ─────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ─────────────────────────────────────────────

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

        chunks = self._split_into_chunks(sentences, self.SCENE_CHUNK_SIZE)
        print(
            f"🎬 Scene analysis: {len(sentences)} sentences → {len(chunks)} chunks (chunk_size={self.SCENE_CHUNK_SIZE})"
        )

        all_chunk_scenes: List[List[Dict]] = []
        for i, chunk in enumerate(chunks):
            first = chunk[0]["sentence_index"]
            last = chunk[-1]["sentence_index"]
            print(f"   Chunk {i+1}/{len(chunks)}: s{first}–s{last}")
            chunk_scenes = self._detect_scene_boundaries(chunk, style)
            all_chunk_scenes.append(chunk_scenes)
            print(f"   → {len(chunk_scenes)} scene(s) detected")

        merged_scenes = self._merge_chunk_scenes(all_chunk_scenes)
        print(f"   → merged: {len(merged_scenes)} scene(s) total")

        sent_map = {s["sentence_index"]: s["text"] for s in sentences}
        results = []

        for scene in merged_scenes:
            s_start = scene["sentence_start"]
            s_end = scene["sentence_end"]
            desc = scene["scene_description"]

            scene_sentences = [
                sent_map[idx] for idx in range(s_start, s_end + 1) if idx in sent_map
            ]
            scene_text = " ".join(scene_sentences)

            print(f"   🖼 Scene {scene['scene_index']}: s{s_start}–s{s_end} | {desc}")
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

    # ─────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────

    def _split_into_chunks(
        self, sentences: List[Dict], chunk_size: int
    ) -> List[List[Dict]]:
        if len(sentences) <= chunk_size:
            return [sentences]
        overlap = 2
        chunks, i = [], 0
        while i < len(sentences):
            chunk = sentences[i : i + chunk_size]
            chunks.append(chunk)
            if i + chunk_size >= len(sentences):
                break
            i += chunk_size - overlap
        return chunks

    def analyze_master_scene(self, chapter_text: str, style: str) -> Optional[Dict]:
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

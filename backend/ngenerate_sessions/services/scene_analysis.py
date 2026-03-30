import json
import re
import requests
from typing import Dict, List, Optional, Tuple

from ngenerate_sessions.services.lora_config import get_lora_config


class SceneAnalysis:

    SCENE_CHUNK_SIZE = 20
    MAX_SCENES_PER_CHUNK = 3
    MIN_SENTENCES_PER_SCENE = 3

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
        """ทำความสะอาด tags และลบ banned tags"""
        if not text:
            return ""

        tags = [t.strip() for t in text.replace("\n", " ").split(",") if t.strip()]

        clean = []
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower in self.__BANNED_TAGS:
                continue
            if tag not in clean:
                clean.append(tag[:50])

        if len(clean) > 35:
            clean = clean[:35]

        return ", ".join(clean)

    def _build_scene_prefix(self, style: str) -> str:
        config = get_lora_config(style)
        parts = [config["score_prefix"], self.__SCENE_FRAMING, config["style_tags"]]
        if config["trigger_word"]:
            parts.append(config["trigger_word"])
        return ", ".join(p for p in parts if p)

    def _build_negative(self, style: str) -> str:
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
    # BOUNDARY DETECTION
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

        Split the story sentences below into {self.MAX_SCENES_PER_CHUNK} scenes or fewer.

        Rules:
        - Each scene must cover a continuous range of sentences
        - Scenes change when: location changes, time passes, mood shifts significantly
        - Minimum {self.MIN_SENTENCES_PER_SCENE} sentences per scene
        - sentence_start and sentence_end must be actual sentence indexes from the list
        - Cover ALL sentences: first={first_idx}, last={last_idx}
        - scene_description: 1 short English phrase describing the environment/setting

        Example output:
        [
        {{"scene_index": 1, "sentence_start": {first_idx}, "sentence_end": {first_idx + 5}, "scene_description": "morning rice field, village path"}},
        {{"scene_index": 2, "sentence_start": {first_idx + 6}, "sentence_end": {last_idx}, "scene_description": "riverside at sunset, bamboo huts"}}
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
    # MERGE SCENES
    # --------------------------------------------------

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

    # --------------------------------------------------
    # BACKGROUND PROMPT GENERATION
    #
    # แก้ปัญหา: scene prompt ไม่สอดคล้องกับเนื้อเรื่อง
    #
    # สาเหตุเดิม:
    #   - LLM รับแค่ scene_description สั้นๆ (เช่น "morning rice field")
    #     และ scene_text แต่ prompt ไม่ได้บังคับให้อ่าน "บรรยากาศ" จาก event
    #   - LLM มักคืน tags สวยงามทั่วไป ("misty morning", "golden light")
    #     แทนที่จะสะท้อนเหตุการณ์ เช่น ถ้าฉากมีการต่อสู้ก็ควรมี
    #     "dust cloud", "broken pillars", "scattered debris"
    #
    # วิธีแก้:
    #   1. เพิ่ม "scene_mood" extraction step — ให้ LLM ระบุ mood/event
    #      จาก scene_text ก่อน แล้วนำไปใช้ใน prompt generation
    #   2. แยก prompt เป็น 2 ส่วน: environment tags + atmosphere tags
    #      atmosphere tags มาจาก mood ของ scene จริงๆ
    #   3. ถ้า scene มี action keywords (fight, battle, run, escape)
    #      ให้เพิ่ม atmospheric visual cues อัตโนมัติ
    # --------------------------------------------------

    # Keyword → atmosphere visual cues
    # ใช้ detect จาก scene_text และ scene_description แล้วเพิ่มเป็น hint ให้ LLM
    __MOOD_CUES = {
        "fight": "dust cloud, debris scattered, tense atmosphere, dynamic lighting",
        "battle": "smoke in air, battle damage, intense lighting, dark clouds",
        "running": "motion blur trees, kicked up dust, urgent atmosphere",
        "escape": "shadows, narrow path, urgent lighting, overgrown surroundings",
        "death": "dim lighting, fallen leaves, somber atmosphere, grey sky",
        "cry": "rain or mist, soft dim light, lonely atmosphere",
        "night": "moonlight, stars, lantern glow, deep shadows",
        "morning": "soft golden light, mist on ground, dew on leaves",
        "rain": "rain streaks, wet ground, puddles, overcast sky",
        "fire": "fire glow, ember floating, smoke rising, orange light",
        "celebration": "lanterns hanging, festive decorations, warm golden light",
        "training": "training ground, wooden dummies, worn dirt floor, morning mist",
        "ทวน": "weapon rack nearby, training ground, combat-worn environment",
        "ดาบ": "weapon rack nearby, combat-worn stone floor",
        "สู้": "dust cloud, debris, tense atmosphere",
        "วิ่ง": "kicked up dust, motion blur surroundings",
        "ร้องไห้": "soft dim light, lonely atmosphere, mist",
        "ฝึก": "training ground, worn dirt floor, early morning light",
        "ตาย": "fallen leaves, dim light, somber grey sky",
    }

    def _extract_scene_mood_cues(self, scene_text: str, scene_description: str) -> str:
        """
        ตรวจ scene_text และ scene_description ด้วย keyword matching
        คืน atmosphere cue string สำหรับใส่เป็น hint ใน LLM prompt
        """
        combined = (scene_text + " " + scene_description).lower()
        found_cues = []
        seen = set()
        for keyword, cue in self.__MOOD_CUES.items():
            if keyword.lower() in combined and cue not in seen:
                found_cues.append(cue)
                seen.add(cue)
        return ", ".join(found_cues[:3])

    # --------------------------------------------------
    # IMPROVED BACKGROUND PROMPT GENERATION
    # --------------------------------------------------

    # เพิ่ม keyword mapping สำหรับ scene event detection
    __EVENT_KEYWORDS = {
        "combat": {
            "keywords": [
                "fight",
                "battle",
                "combat",
                "duel",
                "struggle",
                "attack",
                "defend",
                "strike",
                "slash",
                "punch",
                "kick",
                "ต่อสู้",
                "สู้",
                "รบ",
                "ประลอง",
                "โจมตี",
            ],
            "visuals": "battle damage, dust cloud, scattered debris, broken weapons, blood spatter on ground, dramatic shadows",
        },
        "training": {
            "keywords": [
                "train",
                "practice",
                "spar",
                "exercise",
                "ฝึก",
                "ซ้อม",
                "ฝึกฝน",
                "ซ้อมต่อสู้",
            ],
            "visuals": "training ground, wooden dummies, worn dirt floor, straw targets, sweat drops, morning light",
        },
        "meditation": {
            "keywords": [
                "meditate",
                "cultivate",
                "sit cross-legged",
                "close eyes",
                "สมาธิ",
                "นั่งสมาธิ",
                "บำเพ็ญ",
                "ฝึกจิต",
            ],
            "visuals": "peaceful atmosphere, soft light rays, incense smoke curling, stone platform, zen garden",
        },
        "conversation": {
            "keywords": [
                "talk",
                "speak",
                "say",
                "discuss",
                "whisper",
                "shout",
                "พูด",
                "คุย",
                "กล่าว",
                "สนทนา",
                "กระซิบ",
            ],
            "visuals": "intimate atmosphere, warm lighting, focused on speakers, comfortable setting",
        },
        "escape": {
            "keywords": [
                "run",
                "escape",
                "flee",
                "dash",
                "sprint",
                "วิ่ง",
                "หนี",
                "หลบหนี",
                "เร่งรีบ",
            ],
            "visuals": "motion blur, kicked up dust, urgent atmosphere, blurred background, speed lines",
        },
        "celebration": {
            "keywords": [
                "celebrate",
                "festival",
                "party",
                "feast",
                "joy",
                "happy",
                "ฉลอง",
                "เทศกาล",
                "งานเลี้ยง",
                "รื่นเริง",
            ],
            "visuals": "lanterns hanging, festive decorations, warm golden light, crowds, colorful banners",
        },
        "funeral": {
            "keywords": [
                "die",
                "death",
                "funeral",
                "grave",
                "corpse",
                "dead",
                "ตาย",
                "มรณะ",
                "ศพ",
                "งานศพ",
            ],
            "visuals": "dim lighting, grey sky, incense smoke, white flowers, somber atmosphere, falling leaves",
        },
        "night": {
            "keywords": [
                "night",
                "evening",
                "dark",
                "moon",
                "stars",
                "midnight",
                "ค่ำ",
                "กลางคืน",
                "มืด",
                "จันทร์",
            ],
            "visuals": "moonlight, starry sky, lantern glow, deep shadows, night atmosphere",
        },
        "morning": {
            "keywords": ["morning", "dawn", "sunrise", "early", "เช้า", "รุ่งอรุณ", "อรุณ"],
            "visuals": "soft golden light, morning mist, dew on leaves, warm sunrise colors",
        },
        "rain": {
            "keywords": ["rain", "raining", "storm", "wet", "ฝน", "ตก", "พายุ"],
            "visuals": "rain streaks, wet ground, puddles, overcast sky, water droplets, mist",
        },
        "fire": {
            "keywords": ["fire", "flame", "burn", "blaze", "ไฟ", "เพลิง", "ลุกไหม้"],
            "visuals": "fire glow, ember floating, smoke rising, orange light, dramatic lighting",
        },
    }

    def _extract_scene_events(
        self, scene_text: str, scene_description: str
    ) -> Tuple[str, str]:
        """
        วิเคราะห์ว่า scene นี้เกิดเหตุการณ์อะไรบ้าง
        คืน (event_type, visual_cues)
        """
        combined = (scene_text + " " + scene_description).lower()
        detected_events = []
        visual_cues = []

        for event, data in self.__EVENT_KEYWORDS.items():
            for keyword in data["keywords"]:
                if keyword.lower() in combined:
                    detected_events.append(event)
                    if data["visuals"] not in visual_cues:
                        visual_cues.append(data["visuals"])
                    break

        # หา event ที่สำคัญที่สุด (ลำดับความสำคัญ)
        priority = [
            "combat",
            "escape",
            "funeral",
            "celebration",
            "training",
            "meditation",
            "conversation",
            "fire",
            "rain",
            "night",
            "morning",
        ]

        primary_event = "neutral"
        for p in priority:
            if p in detected_events:
                primary_event = p
                break

        visual_str = ", ".join(visual_cues[:3])  # จำกัด 3 cues
        return primary_event, visual_str

    def _extract_location_from_text(
        self, scene_text: str, scene_description: str
    ) -> str:
        """
        ดึงข้อมูลสถานที่จากเนื้อหาให้ละเอียดขึ้น
        """
        location_keywords = {
            "temple": ["วัด", "ศาล", "เจดีย์", "พระ", "temple", "shrine", "pagoda"],
            "forest": ["ป่า", "ดง", "เขา", "forest", "woods", "jungle", "mountain"],
            "village": ["หมู่บ้าน", "บ้าน", "village", "town", "community", "ไร่", "นา"],
            "city": ["เมือง", "กรุง", "city", "capital", "town", "ถนน", "ตลาด"],
            "palace": ["วัง", "พระราชวัง", "palace", "castle", "fortress", "ปราสาท"],
            "courtyard": ["ลาน", "สนาม", "courtyard", "yard", "court", "ลานกว้าง"],
            "room": ["ห้อง", "หอ", "chamber", "room", "hall", "บ้าน"],
            "river": ["แม่น้ำ", "ลำธาร", "river", "stream", "creek", "น้ำ"],
            "bridge": ["สะพาน", "bridge", "ทางข้าม"],
            "cave": ["ถ้ำ", "cave", "cavern", "อุโมงค์"],
            "market": ["ตลาด", "market", "bazaar", "ร้านค้า"],
            "inn": ["โรงเตี๊ยม", "ร้านเหล้า", "inn", "tavern", "guest house"],
            "rice field": ["นา", "ทุ่งนา", "rice field", "paddy", "นาข้าว"],
        }

        combined = (scene_text + " " + scene_description).lower()

        for location, keywords in location_keywords.items():
            for kw in keywords:
                if kw in combined:
                    return location

        # ถ้าหาไม่เจอ ให้ลอง extract จาก scene_description
        if scene_description:
            return scene_description.split(",")[0].strip().lower()

        return "generic location"

    def _generate_scene_prompt(
        self, scene_description: str, scene_text: str, style: str
    ) -> Dict:
        """
        Generate scene prompt ที่สอดคล้องกับเนื้อเรื่องมากขึ้น

        แก้ไขแล้ว:
        - วิเคราะห์ event type จาก scene_text
        - เพิ่ม atmospheric cues ที่ตรงกับเหตุการณ์
        - ระบุสถานที่ให้ชัดเจนขึ้น
        - ใช้ scene_text เต็มในการ generate แทนแค่ description
        """
        if len(scene_text) > 3000:
            scene_text = scene_text[:3000] + "..."

        prefix = self._build_scene_prefix(style)
        negative = self._build_negative(style)

        event_type, event_visuals = self._extract_scene_events(
            scene_text, scene_description
        )
        location = self._extract_location_from_text(scene_text, scene_description)

        mood_hint = ""
        if event_visuals:
            mood_hint = f"\n        SCENE EVENT: {event_type}\n        VISUAL CUES REQUIRED: {event_visuals}"

        prompt = f"""You are a Stable Diffusion background prompt engineer.

        Create a detailed background prompt for this scene.

        Scene description: {scene_description}
        Location detected: {location}
        Art style: {style}{mood_hint}

        ACTUAL STORY CONTENT (use this to understand what is HAPPENING):
        \"\"\"{scene_text}\"\"\"

        STRICT RULES:
        1. Generate ONLY visual/scenery tags, NO characters or humans
        2. 20-30 specific comma-separated tags
        3. Order by importance: LOCATION → ARCHITECTURE/PROPS → LIGHTING → WEATHER/ATMOSPHERE
        4. If the story shows FIGHTING/ACTION: include battle damage, dust, dynamic lighting, tension
        5. If the story shows PEACEFUL scene: include calm lighting, serene atmosphere, gentle colors
        6. If the story shows NIGHT/EVENING: include moonlight, shadows, lanterns, stars
        7. NO generic tags like "beautiful landscape", "fantasy scenery", "epic scenery"
        8. ALL tags must be concrete visual elements that reflect the actual scene content

        Example outputs:

        Combat scene in courtyard:
        {{"positive_prompt": "ancient stone courtyard, cracked stone floor, broken wooden training dummies, scattered debris, dust particles floating in air, torch light flickering, dramatic shadows, worn stone steps, battle damage on walls, tense atmosphere, evening light"}}

        Peaceful morning in village:
        {{"positive_prompt": "rural village street, wooden houses with thatched roofs, morning mist rising, dirt path, dewdrops on grass, warm golden sunlight filtering through trees, chickens pecking ground, water well in center, soft haze in distance, calm atmosphere"}}

        Night scene in forest:
        {{"positive_prompt": "dense forest clearing, ancient twisted trees, moonbeams through canopy, glowing fireflies, thick undergrowth, moss-covered rocks, deep shadows, mist rising from ground, silver moonlight, mysterious atmosphere"}}

        Return JSON only with key "positive_prompt":"""

        try:
            raw = self._llm(prompt, temperature=0.65)
            data = self._extract_json_object(raw)

            if "positive_prompt" in data:
                raw_tags = data["positive_prompt"]
            else:
                raw_tags = raw.strip()
                raw_tags = re.sub(r"```(?:json)?", "", raw_tags).strip()
                json_match = re.search(r'"positive_prompt"\s*:\s*"([^"]+)"', raw_tags)
                if json_match:
                    raw_tags = json_match.group(1)

            cleaned = self._clean_tags(raw_tags)

            if len(cleaned.split(",")) < 8:
                location_defaults = {
                    "temple": "ancient temple grounds, stone pagoda, incense smoke",
                    "forest": "dense forest, tall trees, undergrowth",
                    "village": "rural village, wooden houses, dirt path",
                    "city": "ancient city street, stone buildings, market stalls",
                    "courtyard": "stone courtyard, wooden pillars, open sky",
                }
                default = location_defaults.get(location, "story scene setting")
                cleaned = f"{default}, {cleaned}"

            if not cleaned:
                raise ValueError("Empty prompt")

            final_prompt = f"{prefix}, {cleaned}"

            if len(final_prompt) > 500:
                final_prompt = final_prompt[:500]

            return {
                "positive_prompt": final_prompt,
                "negative_prompt": negative,
            }

        except Exception as e:
            print(f"⚠ Scene prompt error: {e}")
            return self._fallback_prompt(style)

    # --------------------------------------------------
    # PUBLIC ENTRY POINT
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

        chunks = self._split_into_chunks(sentences, self.SCENE_CHUNK_SIZE)
        print(
            f"🎬 Scene analysis: {len(sentences)} sentences → "
            f"{len(chunks)} chunks (chunk_size={self.SCENE_CHUNK_SIZE})"
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

    # --------------------------------------------------
    # HELPER
    # --------------------------------------------------

    def _split_into_chunks(
        self, sentences: List[Dict], chunk_size: int
    ) -> List[List[Dict]]:
        if len(sentences) <= chunk_size:
            return [sentences]

        overlap = 2
        chunks = []
        i = 0
        while i < len(sentences):
            chunk = sentences[i : i + chunk_size]
            chunks.append(chunk)
            if i + chunk_size >= len(sentences):
                break
            i += chunk_size - overlap

        return chunks

    # --------------------------------------------------
    # LEGACY
    # --------------------------------------------------

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

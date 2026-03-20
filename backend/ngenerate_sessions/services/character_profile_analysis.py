import json
import re
import requests
from typing import Dict, List


class CharacterProfileAnalysis:
    """
    วิเคราะห์ตัวละครจากเนื้อหา novel แบบ 3-pass

    Pass 1 — Name Detection:
        ดึงชื่อตัวละครจากแต่ละ chunk
        (exclude สัตว์, บุคคลประวัติศาสตร์, คนไม่มีชื่อ)

    Pass 2 — Deduplication + Filter:
        LLM รับ name list ทั้งหมด แล้ว:
        - group ชื่อที่อ้างถึงคนเดียวกัน (เลือกชื่อหลัก)
        - กรองสัตว์ / ไม่ใช่คนออก
        → ได้ canonical name list ที่สะอาด

    Pass 3 — Describe Each Character:
        วิเคราะห์รายละเอียดของตัวละครแต่ละคน
        (sex detection จาก context keyword)
    """

    CHUNK_SIZE = 6000

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

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

    def _extract_json_array(self, text: str) -> list:
        text = re.sub(r"```(?:json)?", "", text).strip()
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            return []
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return []

    def _chunk_text(self, text: str) -> List[str]:
        if len(text) <= self.CHUNK_SIZE:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = start + self.CHUNK_SIZE
            if end >= len(text):
                chunks.append(text[start:])
                break
            cut = text.rfind("\n", start, end)
            if cut == -1:
                cut = end
            chunks.append(text[start:cut])
            start = cut + 1
        return chunks

    def _find_character_passages(self, text: str, name: str, window: int = 800) -> str:
        passages = []
        pos = 0
        count = 0
        while count < 3:
            idx = text.find(name, pos)
            if idx == -1:
                break
            s = max(0, idx - window // 2)
            e = min(len(text), idx + window // 2)
            passages.append(text[s:e])
            pos = idx + len(name)
            count += 1
        return "\n...\n".join(passages) if passages else text[:1500]

    # --------------------------------------------------
    # PASS 1: DETECT CHARACTER NAMES (ต่อ chunk)
    # --------------------------------------------------

    def _detect_names_from_chunk(self, chunk: str) -> List[str]:
        prompt = f"""Read the story below. List named HUMAN characters only.

        STRICT RULES — exclude ALL of these:
        - Animals, horses, pets (e.g. มาหวงเปียว is a horse → exclude)
        - Historical/legendary figures only mentioned in backstory (not present in the scene)
        - Unnamed people ("the man", "a villager", ชายแปลกหน้า, นักเดินทาง)
        - Place names, organization names, sect names (สำนัก, พรรค)
        - Objects or titles without a personal name attached

        INCLUDE only characters who:
        - Have a proper name (given name, nickname, or title+name)
        - Actually appear or speak in the story

        Example output:
        ["หานลี่", "อาสาม", "พ่อหมื่น"]

        Story:
        \"\"\"{chunk}\"\"\"

        Return JSON array only:"""

        try:
            raw = self._llm(prompt, temperature=0.2)
            names = self._extract_json_array(raw)
            return [n for n in names if isinstance(n, str) and 1 < len(n) <= 40]
        except Exception as e:
            print(f"⚠ Name detection error: {e}")
            return []

    def _detect_all_raw_names(self, text: str) -> List[str]:
        chunks = self._chunk_text(text)
        all_names: set = set()
        for chunk in chunks:
            names = self._detect_names_from_chunk(chunk)
            all_names.update(names)
        return list(all_names)

    # --------------------------------------------------
    # PASS 2: DEDUPLICATION + FILTER
    # ปัญหาเดิม: "พอ"/"พ่อ", "อาสาม"/"เจาอวนหาน" ถูกนับแยก
    # --------------------------------------------------

    def _dedup_names(self, names: List[str], story_text: str) -> Dict[str, List[str]]:
        """
        ส่ง name list ทั้งหมดให้ LLM ตรวจว่าชื่อไหนอ้างถึงคนเดียวกัน
        คืน dict: { canonical_name: [alias1, alias2, ...] }
        """
        if not names:
            return {}

        names_str = json.dumps(names, ensure_ascii=False)

        # ส่ง passage สั้นๆ ของแต่ละชื่อเพื่อให้ LLM มี context
        # จำกัดไม่ให้ prompt ยาวเกิน
        context_snippets = {}
        for name in names:
            idx = story_text.find(name)
            if idx != -1:
                s = max(0, idx - 150)
                e = min(len(story_text), idx + 150)
                context_snippets[name] = story_text[s:e]

        context_str = "\n".join(
            f"- {n}: ...{snippet}..."
            for n, snippet in list(context_snippets.items())[:25]
        )

        prompt = f"""You have a list of names extracted from a Thai novel.
        Some names may refer to the same character (nicknames, titles, aliases).

        Your tasks:
        1. GROUP names that refer to the same person → pick the most complete/common name as canonical
        2. REMOVE any non-human entries (animals, horses, places, organizations, sects)
        3. REMOVE duplicates

        Name list:
        {names_str}

        Context snippets:
        {context_str}

        Rules:
        - Keep names exactly as written (Thai script)
        - Each group must represent ONE real human character
        - If unsure whether two names are the same person, keep them separate

        Example output:
        {{
        "characters": [
            {{"canonical": "หานลี่", "aliases": ["เจาบื้อที่สอง", "เสี่ยวลี่"]}},
            {{"canonical": "เจาอวนหาน", "aliases": ["อาสาม"]}},
            {{"canonical": "พ่อหมื่น", "aliases": []}}
        ]
        }}

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.2)
            data = self._extract_json_object(raw)
            characters = data.get("characters", [])

            result = {}
            for item in characters:
                canonical = str(item.get("canonical", "")).strip()
                aliases = [str(a).strip() for a in item.get("aliases", [])]
                if canonical:
                    result[canonical] = aliases

            return result

        except Exception as e:
            print(f"⚠ Dedup error: {e}")
            # fallback: คืนแต่ละชื่อเป็น canonical ของตัวเอง
            return {name: [] for name in names}

    # --------------------------------------------------
    # PASS 3: DESCRIBE EACH CHARACTER
    # --------------------------------------------------

    VALID_AGES = {"child", "teen", "adult", "middle-aged", "elder"}
    VALID_SEXES = {"man", "woman"}

    # keyword ที่บ่งบอกเพศในภาษาไทย — ใช้ให้ LLM hint
    FEMALE_KEYWORDS = "แม่, แม, นาง, หญิง, สาว, พี่สาว, น้องสาว, อา (ผู้หญิง), ฮูหยิน, นางสาว"
    MALE_KEYWORDS = "พ่อ, พอ, นาย, ชาย, หนุ่ม, พี่ชาย, น้องชาย, เจ้า, อา (ผู้ชาย)"

    def _describe_character(self, name: str, aliases: List[str], passage: str) -> dict:
        alias_str = f" (also called: {', '.join(aliases)})" if aliases else ""

        prompt = f"""You are analyzing a character from a Thai novel.

        Character: {name}{alias_str}

        Read the passage carefully and fill in the fields below.
        All field values MUST be in English.

        CRITICAL — sex field:
        - Read pronouns, relationships, and descriptions in the passage
        - Thai male indicators: เขา (he), ชาย, หนุ่ม, นาย, พ่อ, พี่ชาย, น้องชาย, ลุง, อา (uncle)
        - Thai female indicators: เธอ (she), หญิง, สาว, นาง, แม่, พี่สาว, น้องสาว, ป้า, อา (aunt)
        - If the passage uses both, trust the majority
        - Only default to "man" if there is truly NO gender information at all

        Fields:
        - appearance: physical description (hair, eyes, skin, build). Default: "not described"
        - outfit: clothing in the story. Default: "simple casual clothing"
        - sex: "man" or "woman"
        - age: "child" / "teen" / "adult" / "middle-aged" / "elder". Default: "adult"
        - race: ethnicity or fantasy race. Default: "human"
        - base_personality: 1-3 short English traits. Default: "neutral"

        Example output:
        {{
        "name": "หานลี่",
        "appearance": "dark skin, thin build, short black hair, young face",
        "outfit": "simple rural clothing",
        "sex": "man",
        "age": "child",
        "race": "human",
        "base_personality": "curious, determined, mature for his age"
        }}

        Passage:
        \"\"\"{passage}\"\"\"

        Return JSON only:"""

        try:
            raw = self._llm(prompt, temperature=0.3)
            data = self._extract_json_object(raw)
            if not data or not data.get("name"):
                data["name"] = name
            return self._clean_profile(data, name)
        except Exception as e:
            print(f"⚠ Character describe error [{name}]: {e}")
            return self._default_profile(name)

    def _clean_profile(self, data: dict, canonical_name: str) -> dict:
        name = canonical_name  # ใช้ canonical name เสมอ ไม่ใช้จาก LLM response

        sex = str(data.get("sex", "man")).lower().strip()
        if sex not in self.VALID_SEXES:
            sex = "man"

        age = str(data.get("age", "adult")).lower().strip()
        if age not in self.VALID_AGES:
            age = "adult"

        appearance = str(data.get("appearance", "")).strip()
        if not appearance or appearance.lower() in {"unknown", "not mentioned", "none"}:
            appearance = "not described"

        outfit = str(data.get("outfit", "")).strip()
        if not outfit or outfit.lower() in {"unknown", "none", "not mentioned"}:
            outfit = "simple casual clothing"

        race = str(data.get("race", "human")).strip()
        if not race or race.lower() == "unknown":
            race = "human"

        personality = str(data.get("base_personality", "neutral")).strip()
        if not personality or personality.lower() == "unknown":
            personality = "neutral"

        return {
            "name": name,
            "appearance": appearance,
            "outfit": outfit,
            "sex": sex,
            "age": age,
            "race": race,
            "base_personality": personality,
        }

    def _default_profile(self, name: str) -> dict:
        return {
            "name": name,
            "appearance": "not described",
            "outfit": "simple casual clothing",
            "sex": "man",
            "age": "adult",
            "race": "human",
            "base_personality": "neutral",
        }

    # --------------------------------------------------
    # PUBLIC ENTRY POINT
    # --------------------------------------------------

    def run(self, story_text: str) -> Dict:
        """
        วิเคราะห์ตัวละครทั้งหมดจาก story_text แบบ 3-pass

        Returns:
            {"character_profile": [...], "alias_map": {canonical: [aliases]}}
        """
        print("🔍 Pass 1: Detecting character names...")
        raw_names = self._detect_all_raw_names(story_text)
        print(f"   Raw names ({len(raw_names)}): {raw_names}")

        if not raw_names:
            return {"character_profile": [], "alias_map": {}}

        print("🔗 Pass 2: Deduplicating and filtering...")
        canonical_map = self._dedup_names(raw_names, story_text)
        print(
            f"   Canonical characters ({len(canonical_map)}): {list(canonical_map.keys())}"
        )

        print("📝 Pass 3: Describing each character...")
        profiles = []

        for canonical_name, aliases in canonical_map.items():
            # หา passage จากทั้ง canonical name และ aliases
            search_names = [canonical_name] + aliases
            all_passages = []
            for search_name in search_names:
                p = self._find_character_passages(story_text, search_name)
                if p:
                    all_passages.append(p)

            # รวม passages (ไม่ให้ยาวเกิน 2000 chars)
            combined_passage = "\n...\n".join(all_passages)[:2000]

            profile = self._describe_character(
                canonical_name, aliases, combined_passage
            )
            profiles.append(profile)
            print(
                f"   ✓ {canonical_name} (aliases: {aliases}) → {profile['sex']}, {profile['age']}"
            )

        return {
            "character_profile": profiles,
            "alias_map": canonical_map,
        }

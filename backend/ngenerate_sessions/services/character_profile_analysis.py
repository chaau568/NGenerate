# character_profile_analysis.py
import json
import re
import requests
from collections import Counter
from typing import Dict, List


class CharacterProfileAnalysis:

    CHUNK_SIZE = 5000
    MIN_FREQUENCY = 2

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

    # =========================================================
    # HELPERS
    # =========================================================

    def _llm(self, prompt: str, temperature: float = 0.2) -> str:
        payload = {
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }
        response = requests.post(
            f"{self.ai_api_url}/llm/generate", json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()

    def _extract_json_object(self, text: str) -> dict:
        text = re.sub(r"```(?:json)?", "", text).strip()
        start, end = text.find("{"), text.rfind("}")
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

    def _find_passages(
        self, text: str, name: str, n: int = 3, window: int = 600
    ) -> str:
        passages = []
        pos = 0
        while len(passages) < n:
            idx = text.find(name, pos)
            if idx == -1:
                break
            s = max(0, idx - window // 2)
            e = min(len(text), idx + window // 2)
            passages.append(text[s:e])
            pos = idx + len(name)
        return "\n...\n".join(passages) if passages else text[:1200]

    # =========================================================
    # PASS 1: LENIENT NAME EXTRACTION
    # =========================================================

    def _extract_candidates_from_chunk(self, chunk: str, chunk_idx: int) -> List[str]:
        prompt = f"""Read the Thai novel excerpt below and extract ALL possible character names.

CONTEXT: This is a Chinese-style martial arts / cultivation novel translated into Thai.
Character names are often multi-syllable Thai transliterations of Chinese names,
such as "หวังทวนเหล็ก", "หานลี่", "เกาต้าเพิง", "ที่ปรึกษาโจว".
These look like Thai words but ARE personal names of characters.

RULES:
1. Include EVERY string that might be a person's name or title+name:
   - Chinese-style names: "หวังทวนเหล็ก", "หานลี่", "เกาต้าเพิง"
   - Title+name combos: "ที่ปรึกษาโจว", "พ่อบ้านหวัง", "ฮูหยิน"
   - Kinship terms used as names: "พ่อ", "แม่", "อาสาม"
   - Epithets: "ผู้อาวุโส", "เทพขับเคลื่อน"
2. When unsure — INCLUDE IT. We filter later.
3. DO NOT include: place names (แม่น้ำซุ่น), weapon names (ทวนเหล็ก alone), 
   organization names (สำนักเส้าหลิน), abstract concepts.
4. Keep names EXACTLY as written in Thai script.

Story excerpt:
\"\"\"{chunk}\"\"\"

Return JSON array of name strings only. No explanation.
Example: ["หวังทวนเหล็ก", "หานลี่", "ที่ปรึกษาโจว", "เกาต้าเพิง", "ผู้อาวุโส"]"""

        try:
            raw = self._llm(prompt, temperature=0.15)
            names = self._extract_json_array(raw)
            valid = [n for n in names if isinstance(n, str) and 1 < len(n) <= 40]
            print(f"   Chunk {chunk_idx}: found {len(valid)} candidates: {valid}")
            return valid
        except Exception as e:
            print(f"⚠ Pass1 chunk {chunk_idx} error: {e}")
            return []

    def _pass1_extract_all_candidates(self, text: str) -> List[str]:
        chunks = self._chunk_text(text)
        seen: set = set()
        result: List[str] = []
        for i, chunk in enumerate(chunks):
            for name in self._extract_candidates_from_chunk(chunk, i + 1):
                if name not in seen:
                    seen.add(name)
                    result.append(name)
        print(f"   Total unique candidates: {len(result)}")
        return result

    # =========================================================
    # PASS 2: FREQUENCY COUNT (programmatic)
    # BUG FIX: ใช้ word-boundary aware matching เพื่อป้องกัน
    # "แม่" matching กับ "แม่น้ำ"
    # =========================================================

    def _count_as_standalone(self, text: str, name: str) -> int:
        """
        นับจำนวนครั้งที่ name ปรากฏในฐานะ standalone word
        ไม่ใช่ substring ของคำอื่น

        เช่น "แม่" ไม่ควร match กับ "แม่น้ำ"
        แต่ "หวังทวนเหล็ก" ควร match ปกติ
        """
        # สำหรับชื่อยาว (>= 4 ตัวอักษร) ใช้ exact substring ได้เลย
        # เพราะโอกาสที่จะเป็น substring ของคำอื่นน้อยมาก
        if len(name) >= 4:
            return text.count(name)

        # สำหรับชื่อสั้น (2-3 ตัวอักษร) ต้องระวัง false positive
        # ใช้ negative lookaround — อย่านับถ้าตามด้วยอักขระไทยอื่น
        # ที่มักเป็นส่วนของคำ (เช่น แม่น้ำ, พ่อค้า)
        EXTEND_CHARS = set("น้ำคาบ้านครัวยายปู่")  # ตัวอย่างที่มักต่อกับ แม่/พ่อ

        # วิธีง่ายกว่า: นับเฉพาะตำแหน่งที่ตามด้วย space, punctuation หรือ end
        # หรือตามด้วยตัวอักษรไทยที่เริ่มคำใหม่
        count = 0
        pos = 0
        name_len = len(name)
        while True:
            idx = text.find(name, pos)
            if idx == -1:
                break
            end_idx = idx + name_len
            if end_idx < len(text):
                next_char = text[end_idx]
                is_thai_continuation = (
                    "\u0e00" <= next_char <= "\u0e7f"
                    and next_char not in "กขคฆงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ"
                )
                compound_check = text[idx : end_idx + 3]
                known_non_names = [
                    "แม่น้ำ",
                    "แม่ทัพ",
                    "แม่บ้าน",
                    "แม่ครัว",
                    "แม่มด",
                    "พ่อค้า",
                    "พ่อบ้าน",
                ]
                if any(
                    nw.startswith(text[idx : end_idx + len(nw) - name_len])
                    and text[idx:].startswith(nw)
                    for nw in known_non_names
                ):
                    pos = end_idx
                    continue
            count += 1
            pos = end_idx
        return count

    def _pass2_count_frequencies(
        self, candidates: List[str], text: str
    ) -> Dict[str, int]:
        freq: Dict[str, int] = {}
        for name in candidates:
            count = self._count_as_standalone(text, name)
            if count >= self.MIN_FREQUENCY:
                freq[name] = count

        freq = dict(sorted(freq.items(), key=lambda x: x[1], reverse=True))
        print(
            f"   Candidates after frequency filter (>={self.MIN_FREQUENCY}): {len(freq)}"
        )
        print(f"   Top 15: { {k: v for k, v in list(freq.items())[:15]} }")
        return freq

    # =========================================================
    # PASS 3: LLM FILTER + DEDUP
    # =========================================================

    def _get_context_snippet(self, text: str, name: str, window: int = 150) -> str:
        idx = text.find(name)
        if idx == -1:
            return ""
        s = max(0, idx - window // 2)
        e = min(len(text), idx + window // 2)
        return text[s:e].replace("\n", " ")

    def _pass3_filter_and_dedup(
        self, freq_map: Dict[str, int], story_text: str
    ) -> Dict[str, List[str]]:
        if not freq_map:
            return {}

        suspect_names = [n for n, c in freq_map.items() if c <= 5 or len(n) <= 4]
        snippets = {
            name: self._get_context_snippet(story_text, name)
            for name in suspect_names[:25]
            if self._get_context_snippet(story_text, name)
        }

        freq_json = json.dumps(freq_map, ensure_ascii=False, indent=2)
        snippets_str = "\n".join(
            f'  "{name}" ({freq_map[name]}x): "...{snip}..."'
            for name, snip in snippets.items()
        )

        prompt = f"""You are processing character names from a Thai-translated Chinese martial arts novel.

        Name list with frequency counts (how many times each appears in the story):
        {freq_json}

        Context snippets for shorter/ambiguous names:
        {snippets_str if snippets_str else "(none)"}

        YOUR TASKS:

        1. REMOVE non-character entries:
        - Animals or mounts (horses, etc.)
        - Pure place names, river names, sect/organization names
        - Weapon names used alone (not as part of a person's name)
        - Abstract concepts
        
        KEEP:
        - All human characters, including servants, guards, advisors
        - Kinship terms used as character references: "พ่อ", "แม่", "อาสาม"
        - Title+surname combos like "ที่ปรึกษาโจว" (Advisor Zhou) — these ARE characters
        - Epithets like "ผู้อาวุโส", "เทพขับเคลื่อน" if they refer to a specific person
        - ANY name with frequency >= 3 should almost certainly be kept

        2. GROUP aliases of the same person under one canonical name:
        - Choose the most complete/specific name as canonical
        - Example: "หวังทวนเหล็ก", "พ่อบ้านหวัง", "หวัง" → canonical: "หวังทวนเหล็ก"
        - Only merge if confident — when in doubt, keep separate
        - Do NOT merge different characters just because they share a surname

        Output format example:
        {{
        "characters": [
            {{"canonical": "หวังทวนเหล็ก", "aliases": ["พ่อบ้านหวัง", "หวัง"]}},
            {{"canonical": "ที่ปรึกษาโจว", "aliases": []}},
            {{"canonical": "เกาต้าเพิง", "aliases": ["น้องเกา"]}},
            {{"canonical": "ผู้อาวุโส", "aliases": ["เทพขับเคลื่อน"]}}
        ],
        "removed": ["มาหวงเปียว (horse)"]
        }}

        Return JSON only. No explanation."""

        try:
            raw = self._llm(prompt, temperature=0.15)
            data = self._extract_json_object(raw)

            characters = data.get("characters", [])
            removed = data.get("removed", [])
            print(f"   LLM kept: {len(characters)} characters, removed: {len(removed)}")
            if removed:
                print(f"   Removed: {removed[:10]}")

            result: Dict[str, List[str]] = {}
            seen: set = set()
            for item in characters:
                canonical = str(item.get("canonical", "")).strip()
                if not canonical or canonical in seen:
                    continue
                aliases = [
                    str(a).strip() for a in item.get("aliases", []) if str(a).strip()
                ]
                result[canonical] = aliases
                seen.add(canonical)

            all_covered = set(result.keys())
            for aliases_list in result.values():
                all_covered.update(aliases_list)

            for name, count in freq_map.items():
                if count >= 5 and name not in all_covered:
                    print(
                        f"   ⚠ Safety net: restoring high-freq name '{name}' (freq={count})"
                    )
                    result[name] = []

            return result

        except Exception as e:
            print(f"⚠ Pass3 error: {e}")
            return {name: [] for name in freq_map}

    # =========================================================
    # PASS 4: DESCRIBE EACH CHARACTER
    # =========================================================

    VALID_AGES = {"child", "teen", "adult", "middle-aged", "elder"}
    VALID_SEXES = {"man", "woman"}

    def _pass4_describe_character(
        self, name: str, aliases: List[str], passage: str
    ) -> dict:
        alias_str = f" (also known as: {', '.join(aliases)})" if aliases else ""

        prompt = f"""Analyze this character from a Thai-translated Chinese martial arts novel.

        Character: {name}{alias_str}

        Read the passage and fill in ALL fields in ENGLISH.

        SEX DETECTION (critical):
        - Look for pronouns, relationships, physical descriptions
        - Thai male indicators: เขา (he/him), ชาย, หนุ่ม, นาย, พ่อ, พี่ชาย, น้องชาย, ลุง
        - Thai female indicators: เธอ (she/her), หญิง, สาว, นาง, แม่, พี่สาว, น้องสาว, ป้า, ฮูหยิน (noblewoman)
        - Majority rules if mixed signals
        - Default "man" ONLY if truly no gender clues

        FIELDS (all values must be in English):
        - appearance: hair, eyes, skin tone, build, distinguishing features. Default: "not described"
        - outfit: clothing described in the story. Default: "simple clothing"  
        - sex: "man" or "woman"
        - age: "child" / "teen" / "adult" / "middle-aged" / "elder". Default: "adult"
        - race: ethnicity or fantasy race. Default: "human"
        - base_personality: 1-3 English trait words. Default: "neutral"

        Passage:
        \"\"\"{passage}\"\"\"

        Return JSON only:
        {{"name": "{name}", "appearance": "...", "outfit": "...", "sex": "...", "age": "...", "race": "...", "base_personality": "..."}}"""

        try:
            raw = self._llm(prompt, temperature=0.25)
            data = self._extract_json_object(raw)
            return self._clean_profile(data, name)
        except Exception as e:
            print(f"⚠ Pass4 describe error [{name}]: {e}")
            return self._default_profile(name)

    # =========================================================
    # PROFILE HELPERS
    # =========================================================

    def _clean_profile(self, data: dict, canonical_name: str) -> dict:
        def clean_str(val, default):
            v = str(val or "").strip()
            return (
                default
                if not v or v.lower() in {"unknown", "none", "not mentioned", "n/a", ""}
                else v
            )

        sex = str(data.get("sex", "man")).lower().strip()
        if sex not in self.VALID_SEXES:
            sex = "man"

        age = str(data.get("age", "adult")).lower().strip()
        if age not in self.VALID_AGES:
            age = "adult"

        return {
            "name": canonical_name,
            "appearance": clean_str(data.get("appearance"), "not described"),
            "outfit": clean_str(data.get("outfit"), "simple clothing"),
            "sex": sex,
            "age": age,
            "race": clean_str(data.get("race"), "human"),
            "base_personality": clean_str(data.get("base_personality"), "neutral"),
        }

    def _default_profile(self, name: str) -> dict:
        return {
            "name": name,
            "appearance": "not described",
            "outfit": "simple clothing",
            "sex": "man",
            "age": "adult",
            "race": "human",
            "base_personality": "neutral",
        }

    # =========================================================
    # PUBLIC ENTRY POINT
    # =========================================================

    def run(self, story_text: str) -> Dict:
        print("🔍 Pass 1: Extracting name candidates (lenient)...")
        raw_names = self._pass1_extract_all_candidates(story_text)
        print(f"   Raw candidates: {raw_names}")

        if not raw_names:
            return {
                "character_profile": [],
                "alias_map": {},
                "raw_names": [],
                "frequency_map": {},
            }

        print("📊 Pass 2: Counting frequencies (word-boundary aware)...")
        freq_map = self._pass2_count_frequencies(raw_names, story_text)

        if not freq_map:
            print("⚠ No names passed frequency filter")
            return {
                "character_profile": [],
                "alias_map": {},
                "raw_names": raw_names,
                "frequency_map": {},
            }

        print("🔗 Pass 3: LLM filter + dedup...")
        canonical_map = self._pass3_filter_and_dedup(freq_map, story_text)
        print(
            f"   Final characters ({len(canonical_map)}): {list(canonical_map.keys())}"
        )

        print("📝 Pass 4: Describing each character...")
        profiles = []
        for canonical_name, aliases in canonical_map.items():
            all_passages = []
            for search_name in [canonical_name] + aliases:
                p = self._find_passages(story_text, search_name)
                if p:
                    all_passages.append(p)
            combined_passage = "\n...\n".join(all_passages)[:2500]

            profile = self._pass4_describe_character(
                canonical_name, aliases, combined_passage
            )
            profiles.append(profile)
            freq = freq_map.get(canonical_name, 0)
            print(
                f"   ✓ {canonical_name} (freq={freq}, aliases={aliases}) → sex={profile['sex']}, age={profile['age']}"
            )

        return {
            "character_profile": profiles,
            "alias_map": canonical_map,
            "raw_names": raw_names,
            "frequency_map": freq_map,
        }

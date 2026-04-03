import json
import re
import requests
from typing import List, Dict


class SceneCharacterAnalysis:
    """
    วิเคราะห์ว่าตัวละครคนไหนปรากฏในแต่ละ scene
    และแต่ละคน pose/action/expression คืออะไร

    *** output ทั้งหมดต้องเป็น English เท่านั้น ***
    เพื่อให้ Stable Diffusion / SDXL ใช้ได้ถูกต้อง
    """

    # ─────────────────────────────────────────────
    # VALID VALUES (English only, used for sanitizing)
    # ─────────────────────────────────────────────

    VALID_POSES = {
        "standing",
        "sitting",
        "kneeling",
        "lying",
        "crouching",
        "bending over",
        "leaning",
        "floating",
        "running",
        "walking",
        "jumping",
        "falling",
        "climbing",
    }

    VALID_EXPRESSIONS = {
        "neutral",
        "happy",
        "sad",
        "angry",
        "fearful",
        "surprised",
        "determined",
        "calm",
        "confused",
        "worried",
        "excited",
        "tired",
        "smiling",
        "frowning",
        "tearful",
        "disgusted",
        "focused",
        "relieved",
        "embarrassed",
        "cold",
    }

    # Fallback keyword detection (Thai → English action)
    ACTION_MAP: Dict[str, str] = {
        "เดิน": "walking forward",
        "วิ่ง": "running",
        "ยืน": "standing still",
        "นั่ง": "sitting down",
        "คุกเข่า": "kneeling",
        "นอน": "lying down",
        "กราบ": "bowing deeply",
        "ไหว้": "bowing",
        "ชักดาบ": "drawing sword",
        "เก็บดาบ": "sheathing sword",
        "ต่อสู้": "fighting",
        "สู้": "fighting stance",
        "โจมตี": "attacking",
        "ป้องกัน": "defending",
        "ร่ายมนต์": "casting spell",
        "นั่งสมาธิ": "meditating",
        "กิน": "eating",
        "ดื่ม": "drinking",
        "อ่าน": "reading",
        "พูด": "talking",
        "ตะโกน": "shouting",
        "กระซิบ": "whispering",
        "ร้องไห้": "crying",
        "หัวเราะ": "laughing",
        "สั่น": "trembling",
        "ล้ม": "falling down",
        "กระโดด": "jumping",
        "ซ่อน": "hiding",
        "หา": "searching",
        "ชี้": "pointing",
        "จับ": "grabbing",
        "ถือ": "holding",
        "ดึง": "pulling",
        "ผลัก": "pushing",
        "ปีน": "climbing",
        "หนี": "fleeing",
        "ฝึก": "training",
        "ทวน": "practicing sword",
        "ตรวจ": "examining",
        "มอง": "looking intently",
        "จ้อง": "staring",
        "โอบ": "embracing",
    }

    EXPRESSION_MAP: Dict[str, str] = {
        "ยิ้ม": "smiling",
        "หัวเราะ": "happy",
        "ร้องไห้": "tearful",
        "น้ำตา": "tearful",
        "โกรธ": "angry",
        "กริ้ว": "angry",
        "เดือด": "angry",
        "กลัว": "fearful",
        "ตกใจ": "surprised",
        "แปลกใจ": "surprised",
        "ตะลึง": "surprised",
        "เศร้า": "sad",
        "เสียใจ": "sad",
        "งง": "confused",
        "สับสน": "confused",
        "กังวล": "worried",
        "มุ่งมั่น": "determined",
        "ตั้งใจ": "determined",
        "สงบ": "calm",
        "เฉย": "calm",
        "เหนื่อย": "tired",
        "อ่อนเพลีย": "tired",
        "ตื่นเต้น": "excited",
        "หน้าแดง": "embarrassed",
        "ขมวดคิ้ว": "frowning",
        "หน้าบึ้ง": "frowning",
    }

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

    # ─────────────────────────────────────────────
    # LLM + JSON HELPERS
    # ─────────────────────────────────────────────

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

    # ─────────────────────────────────────────────
    # SANITIZE — enforce English output
    # ─────────────────────────────────────────────

    def _is_thai(self, text: str) -> bool:
        """ตรวจว่า string มีอักขระภาษาไทยหรือไม่"""
        return bool(re.search(r"[\u0E00-\u0E7F]", text))

    def _sanitize_action(self, action: str) -> str:
        """
        ถ้า action เป็นภาษาไทย ให้แปลงเป็น English
        ถ้าแปลไม่ได้ ให้ return empty string
        """
        if not action or not action.strip():
            return ""

        action = action.strip()

        if not self._is_thai(action):
            if len(action) > 80:
                return ""
            return action

        for thai_kw, eng_action in self.ACTION_MAP.items():
            if thai_kw in action:
                return eng_action

        return ""

    def _sanitize_expression(self, expression: str) -> str:
        if not expression or not expression.strip():
            return "neutral"

        expression = expression.strip().lower()

        if not self._is_thai(expression):
            if expression in self.VALID_EXPRESSIONS:
                return expression
            if len(expression) < 20:
                return expression
            return "neutral"

        for thai_kw, eng_expr in self.EXPRESSION_MAP.items():
            if thai_kw in expression:
                return eng_expr

        return "neutral"

    def _sanitize_pose(self, pose: str) -> str:
        if not pose or not pose.strip():
            return "standing"

        pose = pose.strip().lower()

        if not self._is_thai(pose):
            if pose in self.VALID_POSES:
                return pose
            # อนุญาต pose ที่ไม่ได้อยู่ใน set ถ้าเป็น English และสั้น
            if len(pose) < 30:
                return pose
            return "standing"

        # แปลง Thai → English pose
        pose_map = {
            "ยืน": "standing",
            "นั่ง": "sitting",
            "คุกเข่า": "kneeling",
            "นอน": "lying",
            "ก้ม": "bending over",
            "วิ่ง": "running",
            "เดิน": "walking",
            "กระโดด": "jumping",
            "ล้ม": "falling",
            "ลอย": "floating",
            "ปีน": "climbing",
            "ซ่อน": "crouching",
        }
        for thai_kw, eng_pose in pose_map.items():
            if thai_kw in pose:
                return eng_pose

        return "standing"

    def _sanitize_result(self, item: dict) -> dict:
        return {
            "name": str(item.get("name", "")).strip(),
            "pose": self._sanitize_pose(str(item.get("pose", "standing"))),
            "action": self._sanitize_action(str(item.get("action", ""))),
            "expression": self._sanitize_expression(
                str(item.get("expression", "neutral"))
            ),
        }

    # ─────────────────────────────────────────────
    # NAME MATCHING
    # ─────────────────────────────────────────────

    def _match_to_known(self, name_raw: str, name_set: set) -> str:
        """จับคู่ชื่อจาก LLM กับ known character names"""
        if name_raw in name_set:
            return name_raw

        # prefix strip
        prefixes = ["คุณ", "ท่าน", "นาย", "นาง", "นางสาว", "พ่อ", "แม่", "พี่", "น้อง", "เจ้า"]
        name_clean = name_raw
        for p in prefixes:
            if name_raw.startswith(p):
                name_clean = name_raw[len(p) :]
                break

        for known in name_set:
            known_clean = known
            for p in prefixes:
                if known.startswith(p):
                    known_clean = known[len(p) :]
                    break
            if (
                name_clean
                and known_clean
                and (
                    name_clean == known_clean
                    or known.startswith(name_raw)
                    or name_raw.startswith(known)
                    or known_clean.startswith(name_clean)
                    or name_clean.startswith(known_clean)
                )
            ):
                return known

        return ""

    def _filter_known(self, results: list, character_names: List[str]) -> list:
        name_set = set(character_names)
        clean = []
        seen_names = set()

        for item in results:
            name_raw = str(item.get("name", "")).strip()
            if not name_raw:
                continue

            matched = self._match_to_known(name_raw, name_set)
            if not matched or matched in seen_names:
                continue

            seen_names.add(matched)
            item["name"] = matched
            clean.append(self._sanitize_result(item))

        return clean

    # ─────────────────────────────────────────────
    # FALLBACK: keyword-based detection
    # ─────────────────────────────────────────────

    def _count_name_in_text(self, text: str, name: str) -> int:
        if len(name) >= 4:
            return text.count(name)

        count = 0
        pos = 0
        name_len = len(name)
        NON_NAME_CONTINUATIONS = [
            "น้ำ",
            "ทัพ",
            "บ้าน",
            "ครัว",
            "มด",
            "ค้า",
            "ยาย",
        ]
        while True:
            idx = text.find(name, pos)
            if idx == -1:
                break
            end_idx = idx + name_len
            suffix = text[end_idx : end_idx + 4]
            is_compound = any(
                suffix.startswith(cont) for cont in NON_NAME_CONTINUATIONS
            )
            if not is_compound:
                count += 1
            pos = end_idx
        return count

    def _fallback_extract_characters(
        self, scene_text: str, character_names: List[str]
    ) -> List[Dict]:
        results = []
        seen = set()

        for name in character_names:
            if name in seen:
                continue

            if self._count_name_in_text(scene_text, name) == 0:
                continue

            sentences = re.split(r"[.!?…\n]+", scene_text)
            action = ""
            expression = "neutral"

            for sent in sentences:
                if self._count_name_in_text(sent, name) == 0:
                    continue

                for thai_kw, eng_action in self.ACTION_MAP.items():
                    if thai_kw in sent:
                        action = eng_action
                        break
                for thai_kw, eng_expr in self.EXPRESSION_MAP.items():
                    if thai_kw in sent:
                        expression = eng_expr
                        break
                break

            results.append(
                {
                    "name": name,
                    "pose": "standing",
                    "action": action,
                    "expression": expression,
                }
            )
            seen.add(name)

        return results

    # ─────────────────────────────────────────────
    # MAIN ANALYSIS
    # ─────────────────────────────────────────────

    def analyze(
        self,
        sentences: List[str],
        character_names: List[str],
        scene_description: str,
    ) -> List[Dict]:
        """
        Returns list of {name, pose, action, expression} — ALL VALUES IN ENGLISH.
        """
        if not sentences or not character_names:
            return []

        # numbered sentences for LLM context
        numbered = []
        for i, sent in enumerate(sentences):
            short = sent[:180] + "..." if len(sent) > 180 else sent
            numbered.append(f"[{i+1}] {short}")

        scene_block = "\n".join(numbered)
        scene_text_full = " ".join(sentences)
        if len(scene_text_full) > 2500:
            scene_text_full = scene_text_full[:2500]

        names_json = json.dumps(character_names, ensure_ascii=False)

        prompt = f"""You are analyzing a scene from a Thai novel for use in Stable Diffusion image generation.

        Scene setting: {scene_description}
        Known characters who could appear: {names_json}

        Story sentences (numbered):
        {scene_block}

        Task: Identify which known characters ACTUALLY appear or are referenced in these sentences.
        For each character found, describe what they are doing for a Stable Diffusion prompt.

        CRITICAL RULES — output must be Stable Diffusion compatible:
        1. "name" must be EXACTLY as listed in the known characters list
        2. "action" must be in ENGLISH — a short visual description of what they are doing physically
        Good: "gripping a sword handle", "sitting cross-legged on stone floor", "bowing with hands clasped", "lying unconscious on ground"
        Bad: Thai text, story dialogue, inner thoughts
        3. "pose" must be ONE English word or short phrase: standing / sitting / kneeling / lying / crouching / bending over / leaning against wall
        4. "expression" must be ONE English emotion word: neutral / happy / sad / angry / fearful / surprised / determined / calm / confused / worried / focused / tired
        5. If a character is only mentioned in thought or memory (not physically present), DO NOT include them
        6. Use empty string "" for action only if the character is truly just standing with no describable action

        Return a JSON array. If no known character appears, return [].

        Example output:
        [
        {{"name": "หานลี่", "action": "gripping wooden sword handle tightly", "pose": "standing", "expression": "determined"}},
        {{"name": "กวนอู", "action": "leaning against stone pillar with arms crossed", "pose": "leaning", "expression": "calm"}},
        {{"name": "สมหมาย", "action": "examining patient's wrist pulse", "pose": "sitting", "expression": "focused"}}
        ]

        JSON array:"""

        try:
            raw = self._llm(prompt, temperature=0.3)
            results = self._extract_json_array(raw)

            if not results:
                obj = self._extract_json_object(raw)
                if obj and "characters" in obj:
                    results = obj["characters"]
                else:
                    raise ValueError("No valid JSON array")

            filtered = self._filter_known(results, character_names)

            if not filtered:
                print(f"   ⚠️ LLM returned no matches, using fallback detection")
                filtered = self._fallback_extract_characters(
                    scene_text_full, character_names
                )

            return filtered

        except Exception as e:
            print(f"⚠ SceneCharacterAnalysis error: {e}, using fallback")
            return self._fallback_extract_characters(scene_text_full, character_names)

import json
import re
import requests
from typing import List, Dict, Set, Tuple


class SceneCharacterAnalysis:
    """
    วิเคราะห์ว่าตัวละครคนไหนปรากฏในแต่ละ scene
    และแต่ละคนอยู่ในท่าทาง/การกระทำ/อารมณ์อะไร

    แก้ไขปัญหาเดิม:
    - LLM ไม่เห็นความสัมพันธ์ระหว่างชื่อกับ action verbs
    - ขาด context ของตัวละครอื่นๆ ใน scene เดียวกัน

    วิธีแก้:
    1. ส่งประโยคแบบมีหมายเลข sentence index
    2. ให้ LLM ระบุ sentence_index ที่พบ action
    3. ใช้ regex fallback เมื่อ LLM ตอบไม่ดี
    """

    # Action keywords mapping สำหรับ fallback detection
    ACTION_KEYWORDS: Dict[str, List[str]] = {
        "walking": ["เดิน", "ก้าว", "ย่าง", "เคลื่อน", "walk", "step"],
        "running": ["วิ่ง", "run", "dash", "sprint", "รีบ"],
        "standing": ["ยืน", "stand", "หยุด", "อยู่"],
        "sitting": ["นั่ง", "sit", "นั่งลง", "นั่งอยู่"],
        "kneeling": ["คุกเข่า", "กราบ", "kneel", "คุก"],
        "lying": ["นอน", "lie", "นอนลง", "นอนราบ"],
        "drawing sword": ["ชักดาบ", "draw sword", "ดึงดาบ", "ชักอาวุธ"],
        "sheathing sword": ["เก็บดาบ", "sheath", "ใส่ฝัก"],
        "bowing": ["คำนับ", "bow", "ก้ม", "น้อม", "ไหว้"],
        "fighting": ["ต่อสู้", "fight", "สู้", "รบ", "โจมตี", "attack"],
        "defending": ["ป้องกัน", "defend", "รับมือ", "block", "parry"],
        "casting spell": ["ร่ายมนต์", "เสก", "spell", "magic", "เวท"],
        "meditating": ["นั่งสมาธิ", "meditate", "ฝึกจิต", "สมาธิ"],
        "eating": ["กิน", "eat", "รับประทาน", "ดื่ม", "drink"],
        "reading": ["อ่าน", "read", "ศึกษา"],
        "talking": ["พูด", "talk", "กล่าว", "บอก", "บอกกล่าว"],
        "shouting": ["ตะโกน", "shout", "ร้อง", "เอ็ด", "ตวาด"],
        "whispering": ["กระซิบ", "whisper", "พูดเบา"],
        "crying": ["ร้องไห้", "cry", "น้ำตา", "สะอื้น", "sobbing"],
        "laughing": ["หัวเราะ", "laugh", "ขบขัน", "ฮ่า"],
        "blushing": ["หน้าแดง", "blush", "แดง", "เขิน"],
        "trembling": ["สั่น", "tremble", "ตัวสั่น", "สั่นเทา", "กลัว"],
        "falling": ["ล้ม", "fall", "หกล้ม", "ร่วง"],
        "jumping": ["กระโดด", "jump", "โดด", "กระโจน"],
        "climbing": ["ปีน", "climb", "ไต่", "ปีนป่าย"],
        "hiding": ["ซ่อน", "hide", "หลบ", "แอบ"],
        "searching": ["หา", "search", "มองหา", "ตามหา"],
        "pointing": ["ชี้", "point", "ชี้นิ้ว"],
        "grabbing": ["จับ", "grab", "คว้า", "ฉวย", "จับต้อง"],
        "pushing": ["ผลัก", "push", "ดัน"],
        "pulling": ["ดึง", "pull", "ลาก"],
        "holding": ["ถือ", "hold", "กำ", "อุ้ม"],
    }

    # Expression keywords
    EXPRESSION_KEYWORDS: Dict[str, List[str]] = {
        "happy": ["ยิ้ม", "ดีใจ", "ปลื้ม", "แฮปปี้", "เบิกบาน", "smile", "joy", "delighted"],
        "sad": ["เศร้า", "เสียใจ", "ทุกข์", "sad", "depressed", "หม่น", "หดหู่"],
        "angry": ["โกรธ", "กริ้ว", "เดือด", "anger", "furious", "ขุ่นเคือง", "ฉุน"],
        "fearful": ["กลัว", "ตกใจ", "หวาดกลัว", "fear", "scared", "terror", "ขวัญหนี"],
        "surprised": [
            "แปลกใจ",
            "ตะลึง",
            "อึ้ง",
            "ตกตะลึง",
            "surprise",
            "shock",
            "astonished",
        ],
        "determined": ["มุ่งมั่น", "ตั้งใจ", "determined", "เด็ดเดี่ยว", "แน่วแน่"],
        "calm": ["ใจเย็น", "สงบ", "calm", "serene", "นิ่ง", "เฉย"],
        "confused": ["งง", "สับสน", "confused", "puzzled", "งุนงง"],
        "worried": ["กังวล", "เป็นห่วง", "worried", "anxious", "ร้อนใจ"],
        "excited": ["ตื่นเต้น", "excited", "คึกคัก", "กระตือรือร้น"],
        "tired": ["เหนื่อย", "อ่อนเพลีย", "tired", "exhausted", "เพลีย"],
        "neutral": ["เฉยเมย", "วางเฉย", "neutral", "ปกติ", "ธรรมดา"],
        "tearful": ["คลอไปด้วยน้ำตา", "watery eyes", "tearful", "น้ำตาคลอ"],
        "smiling": ["ยิ้ม", "ยิ้มแย้ม", "smiling", "ยิ้มน้อย"],
        "frowning": ["ขมวดคิ้ว", "frown", "หน้าบึ้ง", "หน้าบูด"],
    }

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

    def _filter_known(self, results: list, character_names: List[str]) -> list:
        """กรองเฉพาะชื่อที่อยู่ใน character_names"""
        clean = []
        name_set = set(character_names)

        for item in results:
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            matched_name = name
            if name not in name_set:
                for known in name_set:
                    if known.startswith(name) or name.startswith(known):
                        matched_name = known
                        break
                    name_clean = re.sub(
                        r"^(คุณ|ท่าน|นาย|นาง|นางสาว|เด็กชาย|เด็กหญิง|พ่อ|แม่|พี่|น้อง)", "", name
                    )
                    known_clean = re.sub(
                        r"^(คุณ|ท่าน|นาย|นาง|นางสาว|เด็กชาย|เด็กหญิง|พ่อ|แม่|พี่|น้อง)", "", known
                    )
                    if (
                        name_clean
                        and known_clean
                        and (
                            name_clean == known_clean
                            or known_clean.startswith(name_clean)
                        )
                    ):
                        matched_name = known
                        break

            if matched_name not in name_set:
                continue

            clean.append(
                {
                    "name": matched_name,
                    "pose": str(item.get("pose", "standing")).strip() or "standing",
                    "action": str(item.get("action", "")).strip(),
                    "expression": str(item.get("expression", "neutral")).strip()
                    or "neutral",
                }
            )
        return clean

    def _fallback_extract_characters(
        self, scene_text: str, character_names: List[str], scene_description: str
    ) -> List[Dict]:
        """
        Fallback method: ใช้ regex และ keyword detection
        เมื่อ LLM response ไม่ดี
        """
        results = []
        name_set = set(character_names)

        sentences = re.split(r"[.!?…\n]+", scene_text)

        for name in name_set:
            name_variants = [name]
            prefixes = ["คุณ", "ท่าน", "นาย", "นาง", "พ่อ", "แม่", "พี่", "น้อง"]
            for prefix in prefixes:
                name_variants.append(f"{prefix}{name}")
                name_variants.append(f"{prefix} {name}")

            found = False
            action = ""
            expression = "neutral"
            pose = "standing"

            for sent in sentences:
                sent_lower = sent.lower()
                if any(variant in sent for variant in name_variants):
                    found = True
                    for action_name, keywords in self.ACTION_KEYWORDS.items():
                        if any(kw in sent_lower for kw in keywords):
                            action = action_name
                            break
                    for expr_name, keywords in self.EXPRESSION_KEYWORDS.items():
                        if any(kw in sent_lower for kw in keywords):
                            expression = expr_name
                            break
                    break

            if found:
                if action in ["running", "walking", "standing"]:
                    pose = action
                elif action in ["sitting", "kneeling", "lying"]:
                    pose = action

                results.append(
                    {
                        "name": name,
                        "pose": pose,
                        "action": action,
                        "expression": expression,
                    }
                )

        return results

    # --------------------------------------------------
    # MAIN ANALYSIS (IMPROVED)
    # --------------------------------------------------

    def analyze(
        self,
        sentences: List[str],
        character_names: List[str],
        scene_description: str,
    ) -> List[Dict]:
        """
        คืน list ของ {name, pose, action, expression}
        สำหรับตัวละครที่ปรากฏจริงในข้อความของ scene นี้

        แก้ไขแล้ว:
        - ส่งประโยคแบบมีหมายเลข
        - ให้ LLM ระบุ sentence_index ที่พบ action
        - มี fallback detection
        """
        if not sentences or not character_names:
            return []

        numbered_sentences = []
        for i, sent in enumerate(sentences):
            sent_short = sent[:200] + "..." if len(sent) > 200 else sent
            numbered_sentences.append(f"[{i+1}] {sent_short}")

        scene_text_block = "\n".join(numbered_sentences)
        scene_text_full = " ".join(sentences)

        if len(scene_text_full) > 2500:
            scene_text_full = scene_text_full[:2500] + "..."
            scene_text_block = scene_text_block[:3000] + "..."

        names_str = json.dumps(character_names, ensure_ascii=False)

        prompt = f"""You are analyzing a story scene. Identify which characters appear and what they are doing.

        Scene setting: {scene_description}
        Known characters: {names_str}

        Numbered sentences (IMPORTANT - use these numbers to locate actions):
        {scene_text_block}

        For EACH character who appears in this scene, output:
        - name: exact name from known characters list
        - action: what they are DOING (specific action, not just "standing"). 
        Examples: "drawing a sword", "bowing deeply", "punching the wall", "whispering to friend", "gripping sword handle nervously"
        - pose: body position ("standing", "sitting", "kneeling", "lying", "crouching", "bending over")
        - expression: facial emotion ("neutral", "angry", "happy", "sad", "surprised", "fearful", "determined", "confused")

        CRITICAL RULES:
        1. If a character performs a VERB action in the text, include it in "action"
        2. If a character speaks dialogue, include "talking" or "shouting" in action
        3. If a character holds an object (weapon, cup, letter), describe it: "holding a sword", "gripping teacup"
        4. If multiple characters appear, list them all
        5. Use EMPTY string for action if truly no action (just standing still)

        Example output:
        [
        {{"name": "หานลี่", "action": "gripping wooden sword handle", "pose": "standing", "expression": "determined"}},
        {{"name": "พ่อ", "action": "leaning against wall", "pose": "standing", "expression": "calm"}},
        {{"name": "อาสาม", "action": "", "pose": "sitting", "expression": "neutral"}}
        ]

        Return JSON array only:"""

        try:
            raw = self._llm(prompt, temperature=0.35)
            results = self._extract_json_array(raw)

            if not results:
                obj = self._extract_json_object(raw)
                if obj and "characters" in obj:
                    results = obj["characters"]
                else:
                    raise ValueError("No valid JSON array")

            filtered = self._filter_known(results, character_names)

            if not filtered:
                print(f"   ⚠️ LLM returned empty, using fallback detection")
                filtered = self._fallback_extract_characters(
                    scene_text_full, character_names, scene_description
                )

            for item in filtered:
                if not item.get("action"):
                    item["action"] = self._infer_action_from_context(
                        item["name"], scene_text_full, scene_description
                    )

            return filtered

        except Exception as e:
            print(f"⚠ SceneCharacterAnalysis error: {e}, using fallback")
            return self._fallback_extract_characters(
                scene_text_full, character_names, scene_description
            )

    def _infer_action_from_context(
        self, character_name: str, scene_text: str, scene_description: str
    ) -> str:
        """Infer action from context when LLM doesn't provide"""
        text_lower = scene_text.lower()

        for action_name, keywords in self.ACTION_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                for kw in keywords:
                    pattern = rf".{{0,50}}{re.escape(character_name)}.{{0,50}}{re.escape(kw)}|.{0,50}{re.escape(kw)}.{{0,50}}{re.escape(character_name)}"
                    if re.search(pattern, scene_text, re.IGNORECASE):
                        return action_name

        return ""

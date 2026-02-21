import re
import json
import requests
from typing import List
from pythainlp.tokenize import word_tokenize, sent_tokenize
from pythainlp.util import num_to_thaiword


# =========================================================
# PART 1: CONVERT STORY STRING -> JSON (NO FILE I/O)
# =========================================================

class ConvertTextToJson:
    def __init__(self, max_words=180):
        self.max_words = max_words
        self.__TRASH_ONLY_PATTERN = re.compile(r'^[\s\W_ๆ]+$')

    def clean_sentence_strict(self, text: str) -> str:
        if not text:
            return ""

        text = text.strip()
        text = re.sub(r'[\"“”‘’]', '', text)
        text = re.sub(r'[.…]', '', text)
        text = re.sub(r'\s+', ' ', text)

        if self.__TRASH_ONLY_PATTERN.match(text):
            return ""

        return text.strip()

    def normalize_numbers(self, tokens: List[str]) -> List[str]:
        normalized = []
        for t in tokens:
            if t.isdigit():
                try:
                    normalized.append(num_to_thaiword(int(t)))
                except:
                    normalized.append(t)
            else:
                normalized.append(t)
        return normalized

    def split_by_word_limit(self, sentence: str) -> List[str]:
        words = word_tokenize(sentence, engine="newmm")
        words = self.normalize_numbers(words)

        chunks = []
        current = []

        for w in words:
            current.append(w)
            if len(current) >= self.max_words:
                chunks.append("".join(current))
                current = []

        if current:
            chunks.append("".join(current))

        return chunks

    # ===============================
    # NEW INPUT: story string
    # NEW OUTPUT: json list
    # ===============================
    def convert(self, story_text: str):

        raw_text = re.sub(r'[ \t]+', ' ', story_text)
        sentences = sent_tokenize(raw_text, engine="whitespace")

        final_story = []
        index = 1

        for s in sentences:
            s = self.clean_sentence_strict(s)
            if not s:
                continue

            is_dialogue = s.startswith(("\"", "“"))

            parts = self.split_by_word_limit(s)

            for part in parts:
                part = self.clean_sentence_strict(part)
                if not part:
                    continue

                final_story.append({
                    "sentence_index": index,
                    "text": part,
                    "type": "dialogue" if is_dialogue else "narration"
                })
                index += 1

        return final_story


# =========================================================
# PART 2: SENTENCE ANALYSIS (รับ list จาก convert โดยตรง)
# =========================================================

class SentenceAnalysis:

    def __init__(self, ollama_url: str, llama_model: str, timeout: int):
        self.__OLLAMA_URL = ollama_url
        self.__LLAMA_MODEL = llama_model
        self.__TIMEOUT = timeout

    def get_speaker_by_rules(self, text, next_text, prev_text, known_names):
        verbs = r"พูด|ตอบ|เอ่ย|กล่าว|ถาม|ตะโกน|กระซิบ|รำพึง|คิด|ทัก|ร้อง|สั่ง|พึมพำ|นึก|บอก|สอน|อธิบาย"

        check_list = [next_text, text, prev_text]

        for pool in check_list:
            if not pool:
                continue
            for name in known_names:
                if re.search(rf"{name}\s*({verbs})", pool) or re.search(rf"({verbs})\s*{name}", pool):
                    if not re.search(rf"(ถาม|บอก|ทัก|มอง|มองมาที่)\s*{name}", pool):
                        return name
                if f"เสียงของ{name}" in pool or f"เสียง{name}" in pool:
                    return name
        return None

    def analyze_with_llm(self, text, stype, before, after, profiles, history):
        history_str = " -> ".join(history[-5:]) if history else "None"

        prompt = f"""
        Return ONLY JSON. Analyze the speaker and emotion of the 'Target Sentence'.

        Available Characters & Profiles (Use personality and age to judge):
        {profiles}

        Recent Conversation History (Who spoke last): {history_str}

        Context:
        - Before: {before}
        - Target Sentence: "{text}" (Type: {stype})
        - After: {after}

        Instructions:
        1. Identify Speaker: 
        - Use 'base_personality', 'age', and context to judge who is most likely to say this.
        - If it's a wise teaching or a command, it's likely an elder/teacher.
        - If it's a respectful reply or a question, it's likely a junior/student.
        - Names inside quotes (e.g., "Hi, John") are recipients, NOT speakers.
        2. Identify Emotion:
        - You MUST choose ONLY ONE emotion from this list:
          ["neutral", "happy", "sad", "angry", "serious", "fun"]
        - Do NOT create new emotion words.
        - Do NOT explain.
        - If uncertain, choose the closest one.
        - Narration describing action = usually "serious"
        - Jokes or playful teasing = "fun"
        - Commands or warnings = "serious"
        - Strong disagreement or shouting = "angry"
        - Cheerful tone = "happy"
        - Emotional pain or loss = "sad"

        Result format: {{"speaker": "...", "emotion": "..."}}
        """

        try:
            response = requests.post(
                self.__OLLAMA_URL,
                json={
                    "model": self.__LLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9
                    }
                },
                timeout=self.__TIMEOUT
            )
            result = json.loads(response.json()["response"])

            allowed_emotions = {"neutral", "happy", "sad", "angry", "serious", "fun"}

            emotion = str(result.get("emotion", "neutral")).lower()

            if emotion not in allowed_emotions:
                emotion = "neutral"

            speaker = result.get("speaker", "unknown")

            return {
                "speaker": speaker,
                "emotion": emotion
            }

        except:
            return {"speaker": "unknown", "emotion": "neutral"}

    # ======================================
    # NEW: รับ list โดยตรง (ไม่ใช้ไฟล์)
    # ======================================
    def analyze(self, sentence_list, character_profiles):

        profiles = character_profiles
        known_names = [c["name"] for c in profiles]

        results = []
        speaker_history = []

        for i, s in enumerate(sentence_list):

            text = s["text"]
            stype = s["type"]
            before = sentence_list[i-1]["text"] if i > 0 else ""
            after = sentence_list[i+1]["text"] if i + 1 < len(sentence_list) else ""

            if stype == "narration":
                speaker = "narrator"
                analysis = self.analyze_with_llm(text, stype, before, after, profiles, speaker_history)
                emotion = analysis.get("emotion", "neutral")

            else:
                rule_spk = self.get_speaker_by_rules(text, after, before, known_names)
                analysis = self.analyze_with_llm(text, stype, before, after, profiles, speaker_history)
                ai_speaker = analysis.get("speaker", "unknown")
                emotion = analysis.get("emotion", "neutral")

                if rule_spk:
                    speaker = rule_spk
                elif ai_speaker in known_names:
                    speaker = ai_speaker
                else:
                    speaker = speaker_history[-1] if speaker_history else "unknown"

                if speaker != "unknown":
                    speaker_history.append(speaker)

            results.append({
                "sentence_index": s["sentence_index"],
                "text": text,
                "type": stype,
                "speaker": speaker,
                "emotion": str(emotion).lower()
            })

        return results


# =========================================================
# PART 3: COMPLETE PIPELINE (ใช้ใน background task)
# =========================================================

class StoryPipeline:

    def __init__(self, ollama_url, llama_model, timeout=120):
        self.converter = ConvertTextToJson()
        self.analyzer = SentenceAnalysis(ollama_url, llama_model, timeout)

    def process(self, story_text: str, character_profiles: list):

        # 1️⃣ Convert story string -> sentence json
        sentences = self.converter.convert(story_text)

        # 2️⃣ Analyze speaker + emotion
        analyzed = self.analyzer.analyze(sentences, character_profiles)

        return analyzed
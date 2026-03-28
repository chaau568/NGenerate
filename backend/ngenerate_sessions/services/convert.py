import re
from pythainlp.tokenize import sent_tokenize, syllable_tokenize, word_tokenize


class ConvertTextToJson:

    MAX_WORDS = 100

    # --------------------------------------------------
    # Utility: clean / sanitize text ก่อนเข้า NLP
    # --------------------------------------------------
    def _safe_text(self, text: str) -> str:
        if not text:
            return ""

        text = text.strip()

        text = re.sub(r"[\x00-\x1F\x7F]", "", text)

        text = re.sub(r"[^\u0E00-\u0E7Fa-zA-Z0-9\s\.\,\!\?\-]", "", text)

        return text.strip()

    # --------------------------------------------------
    # Split sentences + limit 100 words
    # --------------------------------------------------
    def split_sentences(self, text: str) -> list[str]:
        if not text:
            return []

        text = self._safe_text(text)

        try:
            raw_sentences = sent_tokenize(text)
            if len(raw_sentences) == 1:
                raw_sentences = re.split(r"[\.!\?\n]", text)
        except:
            raw_sentences = text.split("\n")

        clean_sentences = []

        for s in raw_sentences:
            s = s.strip()

            if not s:
                continue

            if not re.search(r"[ก-๙a-zA-Z0-9]", s):
                continue

            words = word_tokenize(s, engine="newmm")
            # words = word_tokenize(s)

            if len(words) <= self.MAX_WORDS:
                clean_sentences.append(s)
                continue

            for i in range(0, len(words), self.MAX_WORDS):
                chunk = " ".join(words[i : i + self.MAX_WORDS]).strip()
                if chunk:
                    clean_sentences.append(chunk)

        return clean_sentences

    # --------------------------------------------------
    # Convert → syllable text (safe)
    # --------------------------------------------------
    def to_syllable_text(self, text: str) -> str:
        text = self._safe_text(text)

        if not text:
            return ""

        if not re.search(r"[ก-๙a-zA-Z0-9]", text):
            return text

        try:
            syllables = syllable_tokenize(text)

            if not syllables:
                return text

            cleaned = [s for s in syllables if s.strip()]

            return "-".join(cleaned) if cleaned else text

        except Exception:
            try:
                words = word_tokenize(text)
                return "-".join(words) if words else text
            except Exception:
                return text

    # --------------------------------------------------
    # Main: text → json
    # --------------------------------------------------
    def text_to_json(self, text: str, start_index: int = 1) -> dict:
        sentences = self.split_sentences(text)

        result = []

        for i, s in enumerate(sentences):
            try:
                tts_text = self.to_syllable_text(s)
            except Exception:
                tts_text = s

            result.append(
                {
                    "sentence_index": start_index + i,
                    "text": s,
                    "tts_text": tts_text,
                }
            )

        return {
            "sentences": result,
            "next_index": start_index + len(sentences),
        }

    # --------------------------------------------------
    # helper สำหรับทั้งไฟล์
    # --------------------------------------------------
    def text_file_to_json(self, text: str) -> dict:
        result = self.text_to_json(text, start_index=1)
        return {"sentences": result["sentences"]}

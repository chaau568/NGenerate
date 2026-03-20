from pythainlp.tokenize import sent_tokenize, syllable_tokenize


class ConvertTextToJson:

    MAX_WORDS = 100

    def split_sentences(self, text: str) -> list[str]:
        raw_sentences = sent_tokenize(text)
        clean_sentences = []

        for s in raw_sentences:
            s = s.strip()
            if not s:
                continue

            words = s.split()

            if len(words) <= self.MAX_WORDS:
                clean_sentences.append(s)
            else:
                for i in range(0, len(words), self.MAX_WORDS):
                    chunk = " ".join(words[i : i + self.MAX_WORDS])
                    clean_sentences.append(chunk)

        return clean_sentences

    def to_syllable_text(self, text: str) -> str:
        syllables = syllable_tokenize(text)
        cleaned = [s for s in syllables if s.strip()]
        return "-".join(cleaned)

    def text_to_json(self, text: str, start_index: int = 1) -> dict:
        sentences = self.split_sentences(text)

        result = []
        for i, s in enumerate(sentences):
            result.append(
                {
                    "sentence_index": start_index + i,
                    "text": s,  
                    "tts_text": self.to_syllable_text(s),  
                }
            )

        return {
            "sentences": result,
            "next_index": start_index + len(sentences),
        }

    def text_file_to_json(self, text: str) -> dict:
        result = self.text_to_json(text, start_index=1)
        return {"sentences": result["sentences"]}

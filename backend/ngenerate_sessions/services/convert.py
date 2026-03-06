from pythainlp.tokenize import sent_tokenize


class ConvertTextToJson:

    MAX_WORDS = 250

    def split_sentences(self, text: str):

        # ใช้ PyThaiNLP ตัดประโยค
        raw_sentences = sent_tokenize(text)

        clean_sentences = []

        for s in raw_sentences:
            s = s.strip()
            if not s:
                continue

            words = s.split()

            # ถ้ายาวเกิน 250 คำ → ตัดเพิ่ม
            if len(words) <= self.MAX_WORDS:
                clean_sentences.append(s)
            else:
                for i in range(0, len(words), self.MAX_WORDS):
                    chunk = " ".join(words[i : i + self.MAX_WORDS])
                    clean_sentences.append(chunk)

        return clean_sentences

    def text_file_to_json(self, text: str):

        sentences = self.split_sentences(text)

        return {
            "sentences": [
                {"sentence_index": i + 1, "text": s} for i, s in enumerate(sentences)
            ]
        }

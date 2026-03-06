import json
import requests


class EmotionAnalysis:

    def __init__(self, ollama_url, llama_model, timeout=3600, batch_size=15):
        self.url = ollama_url
        self.model = llama_model
        self.timeout = timeout
        self.batch_size = batch_size

    def analyze_batch(self, batch):

        sentence_block = json.dumps(batch, ensure_ascii=False)

        prompt = f"""
        You are a professional novel literary analyst.

        Your task is to analyze narrative fiction carefully and determine
        the dominant emotional tone of each sentence.

        IMPORTANT RULES:

        1. You MUST choose only one emotion from this list:
        neutral, serious, sad, happy, angry

        2. Do NOT invent new emotion words.
        3. Do NOT use synonyms (no sadness, no excitement, no fear, etc.)
        4. If the sentence is purely descriptive narration with no strong feeling → use "neutral".
        5. If the sentence contains ambition, determination, future goals → use "serious".
        6. If it contains loss, separation, crying, emotional pain → use "sad".
        7. If it contains joy, pride, excitement, happiness → use "happy".
        8. If it contains shouting, conflict, rage, strong confrontation → use "angry".

        Return ONLY valid JSON array.
        Do NOT explain anything.

        Format:
        [
        {{"emotion": "neutral"}}
        ]

        Sentences:
        {sentence_block}
        """

        try:
            response = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3},
                },
                timeout=self.timeout,
            )

            raw_text = response.json().get("response", "")

            import re

            match = re.search(r"\[.*\]", raw_text, re.DOTALL)
            if not match:
                return []

            data = json.loads(match.group(0))

            valid_indexes = {s["sentence_index"] for s in batch}

            cleaned = []
            for item in data:
                if (
                    isinstance(item, dict)
                    and item.get("sentence_index") in valid_indexes
                    and item.get("emotion")
                    in ["neutral", "serious", "sad", "happy", "angry"]
                ):
                    cleaned.append(item)

            return cleaned

        except Exception as e:
            print("⚠ Emotion LLM Error:", e)
            return []

    def run(self, story_json):

        sentences = story_json["sentences"]
        results = []

        for i in range(0, len(sentences), self.batch_size):
            batch = sentences[i : i + self.batch_size]
            batch_result = self.analyze_batch(batch)
            results.extend(batch_result)

        return results

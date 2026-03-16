import json
import requests


class DisplayCharacterAnalysis:

    def __init__(self, ai_api_url: str, timeout: int, batch_size=20):
        self.ai_api_url = ai_api_url
        self.timeout = timeout
        self.batch_size = batch_size

    def analyze_batch(self, batch, character_profiles):

        sentence_block = json.dumps(batch, ensure_ascii=False)
        char_context = json.dumps(character_profiles, ensure_ascii=False)

        prompt = f"""
        You are a professional fiction scene director.

        Your task:
        Determine which characters should visually appear in each sentence
        as if this story is being adapted into a visual novel or animation.

        Available Characters:
        {char_context}

        Rules:

        1. A character should appear if:
        - Their name is mentioned.
        - The sentence clearly describes their actions.
        - The sentence describes their thoughts or feelings.
        - The narration is centered around them.

        2. Do NOT return characters that are not in the provided list.

        3. Do NOT guess new characters.

        4. If no character is clearly present in a sentence, skip that sentence.

        Return ONLY valid JSON array.

        Format:
        [
        {{"name": "อูคุง", "sentence_index": 3}}
        ]

        Sentences:
        {sentence_block}
        """

        payload = ({"prompt": prompt, "options": {"temperature": 0.2, "top_p": 0.9, "repeat_penalty": 1.1,}})

        try:
            response = requests.post(
                f"{self.ai_api_url}/llm/generate",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()
            raw = response.json().get("response", "")

            import re

            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if not match:
                return []

            data = json.loads(match.group(0))

            valid_indexes = {s["sentence_index"] for s in batch}
            valid_names = {c["name"] for c in character_profiles}

            cleaned = []
            for item in data:
                if (
                    isinstance(item, dict)
                    and item.get("name") in valid_names
                    and item.get("sentence_index") in valid_indexes
                ):
                    cleaned.append(item)

            return cleaned

        except Exception as e:
            print("⚠ Display LLM Error:", e)
            return []

    def run(self, story_json, character_profiles):

        sentences = story_json["sentences"]
        character_map = {}

        for i in range(0, len(sentences), self.batch_size):
            batch = sentences[i : i + self.batch_size]

            # ✅ pre-filter ก่อนส่งเข้า LLM
            filtered_batch = []
            for s in batch:
                for c in character_profiles:
                    if c["name"] in s["text"]:
                        filtered_batch.append(s)
                        break

            # ถ้าไม่มีชื่อเลย → ข้าม LLM
            if not filtered_batch:
                continue

            batch_result = self.analyze_batch(filtered_batch, character_profiles)

            for item in batch_result:
                if not isinstance(item, dict):
                    continue

                name = item.get("name")
                idx = item.get("sentence_index")

                if not name or not idx:
                    continue

                if name not in character_map:
                    character_map[name] = []

                character_map[name].append(idx)

        return {
            "display_characters": [
                {"name": name, "sentence_index_range": sorted(set(idxs))}
                for name, idxs in character_map.items()
            ]
        }

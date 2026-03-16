import json
import requests
from typing import Dict


class CharacterProfileAnalysis:

    def __init__(self, ai_api_url: str, timeout: int):
        self.ai_api_url = ai_api_url
        self.timeout = timeout

    # -------------------------------------------------
    # Extract context (better for long novels)
    # -------------------------------------------------

    def _extract_story_context(self, text: str) -> str:

        MAX_CONTEXT = 16000

        if len(text) <= MAX_CONTEXT:
            return text

        parts = []

        step = len(text) // 5

        for i in range(5):
            start = i * step
            end = start + 3200
            parts.append(text[start:end])

        return "\n...\n".join(parts)

    # -------------------------------------------------
    # Validate + clean
    # -------------------------------------------------

    def validate_and_clean_generic(self, data: Dict) -> Dict:

        profiles = data.get("character_profile", [])

        if not isinstance(profiles, list):
            return {"character_profile": []}

        unique_profiles = []
        seen = set()

        VALID_AGES = {"child", "teen", "adult", "middle-aged", "elder"}
        VALID_SEXES = {"man", "woman"}

        for char in profiles:

            name = str(char.get("name", "")).strip()

            if not name or len(name) < 2:
                continue

            if name in seen:
                continue

            seen.add(name)

            sex = str(char.get("sex", "man")).lower()
            if sex not in VALID_SEXES:
                sex = "man"

            age = str(char.get("age", "adult")).lower()
            if age not in VALID_AGES:
                age = "adult"

            appearance = str(char.get("appearance", "")).strip()
            if not appearance or appearance.lower() in {"unknown", "not mentioned"}:
                appearance = "not described"

            outfit = str(char.get("outfit", "")).strip()
            if not outfit or outfit.lower() in {"unknown", "none", "not mentioned"}:
                outfit = "simple casual clothing"

            race = str(char.get("race", "")).strip()
            if not race or race.lower() == "unknown":
                race = "human"

            personality = str(char.get("base_personality", "")).strip()
            if not personality or personality.lower() == "unknown":
                personality = "neutral"

            clean = {
                "name": name,
                "appearance": appearance,
                "outfit": outfit,
                "sex": sex,
                "age": age,
                "race": race,
                "base_personality": personality,
            }

            unique_profiles.append(clean)

        return {"character_profile": unique_profiles}

    # -------------------------------------------------
    # MAIN
    # -------------------------------------------------

    def run(self, story_text: str) -> Dict:

        print("🚀 Starting character analysis...")

        context = self._extract_story_context(story_text)

        prompt = f"""
You are a professional novel analysis AI.

Your task is to extract ALL named characters appearing in the story.

CRITICAL LANGUAGE RULES

Character names:
- MUST remain exactly as written in the story
- DO NOT translate
- DO NOT romanize

All other fields:
- MUST be written in English only

--------------------------------------------------

EXTRACTION PROCESS

Step 1:
Carefully read the story and detect every named character.

Step 2:
Create one profile per character.

Include:
- main characters
- supporting characters
- relatives
- named villagers
- teachers
- masters
- any named person

Exclude:
- unnamed people
- crowds

--------------------------------------------------

FIELD RULES

appearance:
Describe physical look from the story.

Examples:
- dark rural skin
- thin boy
- round face
- small build
- long hair

If not described:
"use 'not described'"

outfit:
Clothing worn in the story.

Examples:
- worn village clothes
- simple cotton robe
- farmer clothing

If not described:
"use 'simple clothing'"

sex:
man or woman

age:
child, teen, adult, middle-aged, elder

race:
default = human

base_personality:
short trait

Examples:
calm
brave
clever
ambitious
kind

--------------------------------------------------

RETURN FORMAT

Return ONLY JSON

NO markdown
NO explanation
NO text outside JSON

Return up to 25 characters if they exist.

--------------------------------------------------

Story:

\"\"\"{context}\"\"\"

Return JSON:

{{
"character_profile":[
{{
"name":"<Thai name>",
"appearance":"<English>",
"outfit":"<English>",
"sex":"<man/woman>",
"age":"<child/teen/adult/middle-aged/elder>",
"race":"<race>",
"base_personality":"<trait>"
}}
]
}}
"""

        payload = {
            "prompt": prompt,
            "options": {
                "temperature": 0.6,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            },
        }

        try:

            response = requests.post(
                f"{self.ai_api_url}/llm/generate",
                json=payload,
                timeout=self.timeout,
            )

            response.raise_for_status()

            text = response.json()["response"].strip()

            # remove markdown
            if "```" in text:
                parts = text.split("```")
                if len(parts) >= 2:
                    text = parts[1].replace("json", "").strip()

            start = text.find("{")
            end = text.rfind("}")

            if start != -1 and end != -1:
                text = text[start : end + 1]

            raw = json.loads(text)

            if isinstance(raw, list):
                raw = {"character_profile": raw}

            return self.validate_and_clean_generic(raw)

        except Exception as e:

            print(f"❌ Character analysis error: {e}")

            return {"character_profile": []}

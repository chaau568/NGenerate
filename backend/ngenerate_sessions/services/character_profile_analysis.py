import json
import requests
from pathlib import Path
from typing import Dict

class CharacterProfileAnalysis:
    def __init__(self, ollama_url: str, llama_model: str, timeout: int):
        self.__OLLAMA_URL = ollama_url
        self.__LLAMA_MODEL = llama_model
        self.__TIMEOUT = timeout
        
    def validate_and_clean_generic(self, data: Dict) -> Dict:
        profiles = data.get("character_profile", [])
        if not profiles:
            return {"character_profile": []}
        
        unique_profiles = []
        seen_names = set()

        VALID_AGES = ["child", "teen", "adult", "middle-aged", "elder"]
        VALID_SEXES = ["man", "woman"]

        for char in profiles:
            name = char.get("name", "").strip()
            if not name or len(name) < 2:
                continue

            if name not in seen_names:
                # มาตรฐาน Sex
                char["sex"] = str(char.get("sex", "man")).lower()
                if char["sex"] not in VALID_SEXES:
                    char["sex"] = "man"
                
                # มาตรฐาน Age
                char["age"] = str(char.get("age", "adult")).lower()
                if char["age"] not in VALID_AGES:
                    char["age"] = "adult"

                # ตรวจสอบและตั้งค่า Default ตามเงื่อนไขใหม่
                char["appearance"] = char.get("appearance", "unknown")
                
                # เงื่อนไข: ถ้า outfit ไม่มีหรือเป็นค่าว่าง ให้ใช้ "neat outfit"
                outfit = char.get("outfit", "").strip()
                if not outfit or outfit.lower() == "unknown":
                    char["outfit"] = "neat outfit"
                else:
                    char["outfit"] = outfit

                char["race"] = char.get("race", "").strip()
                if not char["race"] or char["race"].lower() == "unknown":
                    char["race"] = "human"

                char["base_personality"] = char.get("base_personality", "").strip()
                if not char["base_personality"] or char["base_personality"].lower() == "unknown":
                    char["base_personality"] = "neutral"

                # ลบ field emotion ออกตามคำขอ
                if "emotion" in char:
                    del char["emotion"]
                
                unique_profiles.append(char)
                seen_names.add(name)

        return {"character_profile": unique_profiles}
    
    def analyze_novel_generic(self, input_path: Path) -> Dict:
        if not input_path.exists():
            print(f"❌ Error: File not found at {input_path}")
            return {}

        with open(input_path, "r", encoding="utf-8") as f:
            story_text = f.read()

        prompt = f"""
        You are a strict JSON extraction system.

        Return ONLY valid JSON.
        Do NOT include explanations, markdown, or extra text.

        Important: The story contains more than one character.
        You MUST return every character you find.

        Task:
        Extract ALL characters appearing in the story.
        If there are multiple characters, include ALL of them.
        Minimum output: 2 characters if at least 2 exist.

        Strict Rules:
        1. "name" MUST be exactly the character name from the novel (Thai only).
        2. All other fields MUST be written in English only.
        3. "appearance" = physical traits only (hair, eyes, body, face).
        4. "outfit" = clothing description. If missing, use "neat outfit".
        5. "sex" MUST be only "man" or "woman".
        6. "age" MUST be one of: child, teen, adult, middle-aged, elder
        7. "race" MUST be species (human, elf, demon, etc). Default = human.
        8. "base_personality" MUST be a short English trait (calm, brave, cruel).
        9. DO NOT include "emotion".
        10. Do NOT copy placeholder values. Generate real data from the story.

        Story Content:
        \"\"\"{story_text[:10000]}\"\"\"

        Output JSON Schema:
        {{
        "character_profile": [
            {{
            "name": "<Thai name>",
            "appearance": "<English appearance>",
            "outfit": "<English outfit or neat outfit>",
            "sex": "<man/woman>",
            "age": "<child/teen/adult/middle-aged/elder>",
            "race": "<race>",
            "base_personality": "<personality>"
            }}
        ]
        }}
        """

        payload = {
            "model": self.__LLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(self.__OLLAMA_URL, json=payload, timeout=self.__TIMEOUT)
            response.raise_for_status()
            raw_data = json.loads(response.json().get("response", "{}"))
            
            return self.validate_and_clean_generic(raw_data)
            
        except Exception as e:
            print(f"❌ API Error: {e}")
            return {}
        
    def run(self, story_text: str, existing_profiles: list = None) -> Dict:

        print("🚀 Starting character analysis...")

        existing_context = ""

        if existing_profiles:
            existing_context = json.dumps(existing_profiles, ensure_ascii=False)

        prompt = f"""
        You are a strict JSON extraction system.

        Return ONLY valid JSON.
        Do NOT include explanations, markdown, or extra text.

        Important: The story contains more than one character.
        If a character already exists in the Existing Character Profiles,
        update their information only if new details appear.
        Do NOT duplicate characters.
        
        Existing Character Profiles:
        {existing_context}

        Task:
        Extract ALL characters appearing in the story.
        If there are multiple characters, include ALL of them.

        Strict Rules:
        1. "name" MUST be exactly the character name from the novel (Thai only).
        2. All other fields MUST be written in English only.
        3. "appearance" = physical traits only (hair, eyes, body, face).
        4. "outfit" = clothing description. If missing, use "neat outfit".
        5. "sex" MUST be only "man" or "woman".
        6. "age" MUST be one of: child, teen, adult, middle-aged, elder
        7. "race" MUST be species (human, elf, demon, etc). Default = human.
        8. "base_personality" MUST be a short English trait (calm, brave, cruel).
        9. DO NOT include "emotion".
        10. Do NOT copy placeholder values. Generate real data from the story.
        11. If a character exists, merge new info carefully.
        
        Story Content:
        \"\"\"{story_text[:12000]}\"\"\"

        Output JSON Schema:
        {{
        "character_profile": [
            {{
            "name": "<Thai name>",
            "appearance": "<English appearance>",
            "outfit": "<English outfit or neat outfit>",
            "sex": "<man/woman>",
            "age": "<child/teen/adult/middle-aged/elder>",
            "race": "<race>",
            "base_personality": "<personality>"
            }}
        ]
        }}
        """

        payload = {
            "model": self.__LLAMA_MODEL,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9
            }
        }

        try:
            response = requests.post(
                self.__OLLAMA_URL,
                json=payload,
                timeout=self.__TIMEOUT
            )
            response.raise_for_status()

            raw_data = json.loads(response.json().get("response", "{}"))

            cleaned = self.validate_and_clean_generic(raw_data)

            return cleaned

        except Exception as e:
            print(f"❌ API Error: {e}")
            return {"character_profile": []}
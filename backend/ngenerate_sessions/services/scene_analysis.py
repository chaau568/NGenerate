import json
import requests
from typing import Dict, Optional


class SceneAnalysis:
    def __init__(self, ollama_url: str, llama_model: str, timeout: int):
        self.__OLLAMA_URL = ollama_url
        self.__LLAMA_MODEL = llama_model
        self.__TIMEOUT = timeout
        self.__FIXED_NEGATIVE_PROMPT = (
            "score_6, score_5, score_4, (low quality, worst quality:1.4), "
            "human, people, person, man, woman, boy, girl, character, "
            "bad anatomy, text, watermark, logo, 3d, realistic"
        )

    def analyze_master_scene(self, chapter_text: str, style: str) -> Optional[Dict]:
        style_guidance = {
            "Chinese": "ancient Chinese architecture, pagodas, ink wash, ghibli style nature",
            "Japanese": "traditional Japanese shrines, cherry blossoms, studio ghibli aesthetic",
            "Futuristic": "cyberpunk cityscapes, neon glow, cinematic anime scenery",
            "Medieval": "European castles, lush green fields, studio ghibli landscape style",
            "Ghibli": "studio ghibli style, lush nature, watercolor-like, hand-painted background",
        }

        ALLOWED_STYLE = {
            "chinese",
            "japanese",
            "futuristic",
            "medieval",
            "modern",
            "ghibli",
        }

        if style not in ALLOWED_STYLE:
            style = "ghibli"

        style_detail = style_guidance.get(
            style, "studio ghibli style, hand-painted background"
        )

        truncated_text = chapter_text

        prompt = f"""
        Role: Professional AI Prompt Engineer for Pony Diffusion V6 XL.
        Task: Create a BACKGROUND SCENERY prompt (No characters).
        
        STYLE CONTEXT: {style} ({style_detail})
        
        PONY XL RULES:
        - START with: "score_9, score_8_up, score_7_up, source_anime, scenery,"
        - Use comma-separated TAGS only. No full sentences.
        - FOCUS: Landscape, architecture, and atmosphere.
        - NO HUMANS: Strictly exclude any mention of people or living beings.
        - Camera MUST be fixed to: eye level view, wide shot
        - Do NOT change camera angle

        Chapter Content:
        {truncated_text}

        ---
        STRUCTURE (8 Parts):
        1. Rating: score_9, score_8_up, score_7_up, source_anime, scenery.
        2. Main Subject: {style} landscape/buildings from chapter.
        3. Nature & Weather: (e.g., clouds, rain, sunlight, forest).
        4. Detail: (e.g., intricate architecture, mossy stones).
        5. Atmosphere: (e.g., serene, peaceful, ethereal).
        6. Lighting: (e.g., soft sunlight, golden hour, dappled light).
        7. eye level view, wide shot
        8. Art Style: {style} style, studio ghibli aesthetics, masterpiece.
        
        OUTPUT FORMAT:
        Return ONLY a JSON object: {{"positive_prompt": "tags here"}}
        """

        try:
            response = requests.post(
                self.__OLLAMA_URL,
                json={
                    "model": self.__LLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.7, "top_p": 0.9},
                },
                timeout=self.__TIMEOUT,
            )
            response.raise_for_status()
            raw_response = json.loads(response.json()["response"])

            return {
                "positive_prompt": raw_response.get("positive_prompt", ""),
                "negative_prompt": self.__FIXED_NEGATIVE_PROMPT,
            }
        except Exception as e:
            return {
                "positive_prompt": f"score_9, score_8_up, source_anime, scenery, {style_detail}, lush nature, beautiful landscape",
                "negative_prompt": self.__FIXED_NEGATIVE_PROMPT,
            }

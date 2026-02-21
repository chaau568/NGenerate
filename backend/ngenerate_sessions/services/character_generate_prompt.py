import json
import requests

class GenerateCharacterPrompt:
    def __init__(self, ollama_url: str, llama_model: str, timeout: int):
        self.__OLLAMA_URL = ollama_url
        self.__LLAMA_MODEL = llama_model
        self.__TIMEOUT = timeout
        self.__FIXED_CHAR_NEGATIVE = "score_6, score_5, score_4, (low quality, worst quality:1.4), bad anatomy, 3d, realistic, masterpiece, ultra detailed, text, watermark, logo, background scenery"

    def generate_prompt(self, character_profile_data: dict, mode: str, style: str) -> dict:
        style_guidance = {
            "Chinese": "traditional Chinese hanfu, ornate embroidery, silk robes, ancient eastern accessories, studio ghibli inspired details",
            "Japanese": "kimono, yukata, samurai armor elements, traditional japanese patterns, kanzashi, retro anime feel",
            "Futuristic": "cyberpunk techwear, glowing neon accents, sleek metallic fabrics, tactical gear, sci-fi bodysuit, clean anime lines",
            "Medieval": "tunic, leather boots, iron armor parts, cloak, fantasy medieval attire, hand-painted textures",
            "Modern": "contemporary streetwear, casual hoodie, denim, sneakers, minimalist fashion, soft cinematic lighting",
            "Ghibli": "studio ghibli character design, simple and elegant attire, flowing fabrics, hand-drawn anime aesthetic, vintage anime colors, soft shaded clothing"
        }
        
        ALLOWED_STYLE = {"chinese", "japanese", "futuristic", "medieval", "modern", "ghibli"}
        
        if style not in ALLOWED_STYLE:
            style = "ghibli"
        
        style_details = style_guidance.get(style, f"{style} fashion and elements")
        
        ALLOWED_MODES = {"text-to-image", "image-to-image"}

        if mode not in ALLOWED_MODES:
            mode = "text-to-image"
        
        if mode == "text-to-image":
            instruction = f"""
            Role: Professional AI Prompt Engineer for Pony Diffusion V6 XL.
            Task: Create a tag-based prompt for a character portrait (Half-body).

            STRICT OBJECT RULES:
            - ONLY include animals, weapons, or held items IF explicitly mentioned in the input data.
            - If NO item/animal is mentioned, the character MUST be 'solo' with 'arms at sides' or 'hands in pockets'.
            - DO NOT hallucinate extra companions or objects.

            IMPORTANT RULES FOR PONY MODEL:
            - START with: "score_9, score_8_up, score_7_up, source_anime,"
            - Use comma-separated tags only.
            - FOCUS: Half-body (Head to waist), NO legs, NO feet.
            - BACKGROUND: "simple background, white background" only.

            Follow this order:
            1. Rating: score_9, score_8_up, score_7_up, source_anime.
            2. Identity: 1boy/1girl, solo, (demographic).
            3. Style: {style_details}.
            4. Appearance: Hair, eyes, body type.
            5. Clothing: Based on {style_details}.
            6. Objects/Companions: ONLY if in input (e.g., holding sword, cat on shoulder).
            7. Pose: half body, head to waist, (specific arm pose).
            8. Background: simple background, white background, isolated.
            9. Polish: {style} aesthetics.
            """
        else:
            instruction = f"""
            Task: Create an EMOTION CHANGE prompt for Pony Diffusion.
            Focus: Change ONLY the facial expression while keeping the character consistent.
            
            Structure: 
            score_9, score_8_up, score_7_up, source_anime, [new expression tags], 1girl, solo, same hairstyle, same outfit, half body, simple background, {style} aesthetics.
            """

        prompt = f"""
        Role: Senior Character Designer.
        Input Data: {json.dumps(character_profile_data)}
        {instruction}
        
        Return ONLY a JSON object: {{"positive_prompt": "9-part structured prompt here"}}
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
            result["negative_prompt"] = self.__FIXED_CHAR_NEGATIVE
            return result
        except Exception as e:
            return {"positive_prompt": "", "negative_prompt": self.__FIXED_CHAR_NEGATIVE}
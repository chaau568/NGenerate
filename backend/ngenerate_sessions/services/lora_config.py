# ngenerate_sessions/services/lora_config.py

LORA_CONFIGS = {
    "ghibli": {
        "lora_name": "Ghibli_1.safetensors",
        "lora_strength": 0.85,
        "trigger_word": "",
        "style_tags": "ghibli style, studio ghibli, anime style, soft colors",
        "score_prefix": "score_9, score_8_up, score_7_up, source_anime",
        "score_negative": "score_6, score_5, score_4",
    },
    "chinese": {
        "lora_name": "ChineseStyleIllustration.safetensors",
        "lora_strength": 0.65,
        "trigger_word": "guofeng, chinese style",
        "style_tags": "guofeng, chinese style, chinese illustration, traditional chinese art",
        "score_prefix": "best quality, masterpiece, ultra detailed",
        "score_negative": "",
    },
    "chinese-modern": {
        "lora_name": "StariweiStyle.safetensors",
        "lora_strength": 0.85,
        "trigger_word": "stariwei_style",
        "style_tags": "stariwei_style, xianxia, chinese fantasy, sharp features, hanfu",
        "score_prefix": "score_9, score_8_up, score_7_up, source_anime",
        "score_negative": "score_6, score_5, score_4",
    },
    "fantasy": {
        "lora_name": "Ghibli_1.safetensors",
        "lora_strength": 0.85,
        "trigger_word": "",
        "style_tags": "fantasy art style, painterly, rich colors, magical atmosphere, detailed illustration",
        "score_prefix": "score_9, score_8_up, score_7_up, source_anime",
        "score_negative": "score_6, score_5, score_4",
    },
    "medieval": {
        "lora_name": "Ghibli_1.safetensors",
        "lora_strength": 0.85,
        "trigger_word": "",
        "style_tags": "medieval fantasy art, european medieval style, muted tones, detailed illustration",
        "score_prefix": "score_9, score_8_up, score_7_up, source_anime",
        "score_negative": "score_6, score_5, score_4",
    },
    "futuristic": {
        "lora_name": "Ghibli_1.safetensors",
        "lora_strength": 0.85,
        "trigger_word": "",
        "style_tags": "futuristic sci-fi art, cyberpunk, neon colors, high tech, anime style",
        "score_prefix": "score_9, score_8_up, score_7_up, source_anime",
        "score_negative": "score_6, score_5, score_4",
    },
}

DEFAULT_STYLE = "ghibli"


def get_lora_config(style: str) -> dict:
    return LORA_CONFIGS.get(style, LORA_CONFIGS[DEFAULT_STYLE])

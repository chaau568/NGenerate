import logging

from .tts_service import TTSService
from .image_service import ImageService

logger = logging.getLogger(__name__)


class AIService:

    def __init__(self):
        self.tts = TTSService()
        self.image = ImageService()

    # =====================================================
    # VOICE
    # =====================================================

    def generate_voice_with_emotion(self, text, voice_type, emotion):

        logger.info(f"TTS: {voice_type} | emotion={emotion}")

        return self.tts.generate(
            text=text,
            voice_type=voice_type,
            emotion=emotion,
        )

    # =====================================================
    # CHARACTER IMAGE
    # =====================================================

    def generate_character_master(self, character_profile, style):

        return self.image.generate_character_text2image(
            positive_prompt=character_profile.positive_prompt,
            negative_prompt=character_profile.negative_prompt,
            style=style,
        )

    def generate_character_emotion(self, character, reference_image):

        return self.image.generate_character_with_ref(
            positive_prompt=character.positive_prompt,
            negative_prompt=character.negative_prompt,
            reference_image_url=reference_image.url,
        )

    # =====================================================
    # SCENE IMAGE
    # =====================================================

    def generate_scene_image(self, illustration, style):

        return self.image.generate_scene(
            positive_prompt=illustration.positive_prompt,
            negative_prompt=illustration.negative_prompt,
            style=style,
        )

from .tts_service import TTSService
from .image_service import ImageService
from .voice_mapper import VoiceMapper


class AIService:

    def __init__(self):
        self.tts = TTSService()
        self.image = ImageService()

    # =====================================================
    # VOICE
    # =====================================================

    def generate_voice(self, sentence):

        if not sentence.character:
            return None, 0

        profile = sentence.character.profile

        voice_key = VoiceMapper.map_from_profile(
            profile=profile,
            sentence=sentence
        )

        return self.tts.generate(
            text=sentence.sentence,
            voice_key=voice_key
        )

    # =====================================================
    # CHARACTER IMAGE
    # =====================================================

    def generate_character_image(self, character):

        """
        character = Character instance
        Decide workflow automatically
        """

        profile = character.profile

        # ถ้ามี master image → ใช้ image ref workflow
        if profile.master_image_path:
            return self.image.generate_character_with_ref(
                positive_prompt=character.positive_prompt,
                negative_prompt=character.negative_prompt,
                reference_image_url=profile.master_image_path.url
            )

        # ถ้าไม่มี → text to image
        return self.image.generate_character_text2image(
            positive_prompt=character.positive_prompt,
            negative_prompt=character.negative_prompt
        )

    # =====================================================
    # SCENE IMAGE
    # =====================================================

    def generate_scene_image(self, illustration):

        return self.image.generate_scene(
            positive_prompt=illustration.positive_prompt,
            negative_prompt=illustration.negative_prompt
        )
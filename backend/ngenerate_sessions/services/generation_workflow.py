from asset.models import (
    CharacterProfileAsset,
    CharacterAsset,
    NarratorVoice,
    IllustrationImage,
    Video,
)

from ngenerate_sessions.models import (
    Sentence,
    Illustration,
    CharacterProfile,
    Character,
    SentenceCharacter,
)

from .ai_service import AIService
from .timeline_builder import TimelineBuilder
from .video_composer import VideoComposer
from .voice_mapper import VoiceMapper


class GenerationWorkflow:

    def __init__(self, session):
        self.session = session
        self.ai = AIService()

    def run(self):

        self.session.create_processing_steps("generation")

        while True:

            step = (
                self.session.processing_steps.filter(
                    phase="generation", status="pending"
                )
                .order_by("order")
                .first()
            )

            if not step:
                break

            try:

                step.mark_start()

                if step.name == "Generating Character Master Image":
                    self._generate_character_master()

                elif step.name == "Generating Character Emotion Image":
                    self._generate_character_emotion()

                elif step.name == "Generating Scene Image":
                    self._generate_scene()

                elif step.name == "Generating Narrator Voice":
                    self._generate_voice()

                elif step.name == "Composite Video":
                    self._compose_video()

                step.mark_success()
                self.session.update_notification_progress()

            except Exception as e:

                step.mark_failed(str(e))
                self.session.update_notification_progress()
                raise

        self.session.complete_generation()

    # =====================================================
    # 1. CHARACTER MASTER IMAGE
    # =====================================================

    def _generate_character_master(self):

        profiles = CharacterProfile.objects.filter(
            characters__session=self.session
        ).distinct()

        for profile in profiles:

            if hasattr(profile, "asset"):
                continue

            image_file = self.ai.generate_character_master(
                character_profile=profile,
                style=self.session.style
            )

            CharacterProfileAsset.objects.create(
                character_profile=profile,
                image=image_file
            )

    # =====================================================
    # 2. CHARACTER EMOTION IMAGE
    # =====================================================

    def _generate_character_emotion(self):

        characters = Character.objects.filter(
            session=self.session
        ).select_related("character_profile")

        for character in characters:

            if CharacterAsset.objects.filter(character=character).exists():
                continue

            master_asset = character.character_profile.asset

            image_file = self.ai.generate_character_emotion(
                character=character,
                reference_image=master_asset.image
            )

            CharacterAsset.objects.create(
                session=self.session,
                character=character,
                image=image_file
            )

    # =====================================================
    # 3. SCENE IMAGE
    # =====================================================

    def _generate_scene(self):

        illustrations = Illustration.objects.filter(session=self.session)

        for illustration in illustrations:

            if IllustrationImage.objects.filter(illustration=illustration).exists():
                continue

            image_file = self.ai.generate_scene_image(
                illustration=illustration,
                style=self.session.style,
            )

            IllustrationImage.objects.create(
                session=self.session,
                illustration=illustration,
                image=image_file,
            )

    # =====================================================
    # 4. VOICE GENERATION
    # =====================================================

    def _generate_voice(self):

        sentences = Sentence.objects.filter(session=self.session).order_by(
            "chapter__order", "sentence_index"
        )

        for sentence in sentences:

            if NarratorVoice.objects.filter(sentence=sentence).exists():
                continue

            sentence_character = (
                SentenceCharacter.objects.filter(sentence=sentence)
                .select_related("character__character_profile")
                .first()
            )

            if sentence_character:

                profile = sentence_character.character.character_profile

                voice_type, emotion = VoiceMapper.map_from_profile(
                    profile=profile, sentence=sentence
                )

            else:

                voice_type = self.session.narrator_voice
                emotion = sentence.emotion or "neutral"

            audio_file, duration = self.ai.generate_voice_with_emotion(
                text=sentence.sentence, voice_type=voice_type, emotion=emotion
            )

            NarratorVoice.objects.create(
                session=self.session,
                sentence=sentence,
                voice=audio_file,
                duration=duration,
            )

    # =====================================================
    # 5. VIDEO COMPOSE
    # =====================================================

    def _compose_video(self):

        builder = TimelineBuilder(self.session)
        timeline = builder.build()

        composer = VideoComposer(timeline=timeline)

        video_path, video_duration = composer.compose()

        Video.objects.create(
            session=self.session,
            video_file=video_path,
            duration=video_duration,
            is_final=True,
        )

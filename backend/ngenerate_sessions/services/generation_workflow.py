import logging

from asset.models import (
    CharacterProfileAsset,
    CharacterAsset,
    NarratorVoice,
    IllustrationImage,
    Video,
    character_profile_asset_path,
    character_asset_path,
    illustration_image_path,
    narrator_voice_path,
)

from ngenerate_sessions.models import (
    Sentence,
    Illustration,
    CharacterProfile,
    Character,
)

from .ai_service import AIService
from .timeline_builder import TimelineBuilder
from .voice_mapper import VoiceMapper
from asset.models import video_path

logger = logging.getLogger(__name__)


class GenerationWorkflow:

    def __init__(self, session):
        self.session = session
        self.ai = AIService()

    # =====================================================
    # MAIN WORKFLOW
    # =====================================================

    def run(self):

        logger.info(f"Start generation workflow | session={self.session.id}")

        self.session.create_processing_steps("generation")

        while True:

            step = (
                self.session.processing_steps.filter(
                    phase="generation",
                    status="pending",
                )
                .order_by("order")
                .first()
            )

            if not step:
                break

            try:

                logger.info(f"Running step: {step.name}")

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

                logger.exception(e)

                step.mark_failed(str(e))
                self.session.update_notification_progress()

                raise

        logger.info(f"Generation workflow finished | session={self.session.id}")

        if self.session.status == "generating":
            self.session.complete_generation()
        else:
            logger.warning(
                f"Skip complete_generation | session={self.session.id} status={self.session.status}"
            )

    # =====================================================
    # CHARACTER MASTER
    # =====================================================

    def _generate_character_master(self):
        profiles = CharacterProfile.objects.filter(
            characters__session=self.session
        ).distinct()
        for profile in profiles:
            asset, created = CharacterProfileAsset.objects.get_or_create(
                character_profile=profile
            )

            if asset.image and not asset.image.endswith("default_avatar.jpg"):
                continue

            filename = "master.png"
            target_path = character_profile_asset_path(asset, filename)

            image_path = self.ai.generate_character_master(
                character_profile=profile,
                output_path=target_path,
            )

            asset.image = image_path
            asset.save()

    # =====================================================
    # CHARACTER EMOTION
    # =====================================================

    def _generate_character_emotion(self):

        characters = Character.objects.filter(session=self.session).select_related(
            "character_profile", "chapter"
        )

        for character in characters:

            if CharacterAsset.objects.filter(character=character).exists():
                continue

            master_asset = getattr(character.character_profile, "asset", None)

            if not master_asset:
                raise Exception(
                    f"Master image missing for profile: {character.character_profile.id}"
                )

            dummy = CharacterAsset(
                session=self.session,
                character=character,
            )

            filename = "emotion.png"

            output_path = character_asset_path(dummy, filename)

            image_path = self.ai.generate_character_emotion(
                character=character,
                reference_image_path=master_asset.image,
                output_path=output_path,
            )

            CharacterAsset.objects.create(
                session=self.session,
                character=character,
                image=image_path,
            )

    # =====================================================
    # SCENE IMAGE
    # =====================================================

    def _generate_scene(self):

        illustrations = Illustration.objects.filter(session=self.session)

        for illustration in illustrations:

            if IllustrationImage.objects.filter(illustration=illustration).exists():
                continue

            dummy = IllustrationImage(
                session=self.session,
                illustration=illustration,
            )

            filename = "scene.png"

            output_path = illustration_image_path(dummy, filename)

            image_path = self.ai.generate_scene_image(
                illustration=illustration,
                output_path=output_path,
            )

            IllustrationImage.objects.create(
                session=self.session,
                illustration=illustration,
                image=image_path,
            )

    # =====================================================
    # VOICE
    # =====================================================

    def _generate_voice(self):

        sentences = (
            Sentence.objects.filter(session=self.session)
            .select_related("chapter")
            .order_by("chapter__order", "sentence_index")
        )

        for sentence in sentences:

            if NarratorVoice.objects.filter(sentence=sentence).exists():
                continue

            voice_type, emotion, config = VoiceMapper.map(
                session=self.session,
                sentence=sentence,
            )

            dummy = NarratorVoice(
                session=self.session,
                sentence=sentence,
            )

            filename = "voice.wav"

            output_path = narrator_voice_path(dummy, filename)

            voice_path, duration = self.ai.generate_voice_with_emotion(
                text=sentence.sentence,
                voice_type=voice_type,
                emotion=emotion,
                output_path=output_path,
                **config,
            )

            NarratorVoice.objects.create(
                session=self.session,
                sentence=sentence,
                voice=voice_path,
                duration=duration,
            )

    # =====================================================
    # VIDEO
    # =====================================================

    def _compose_video(self):

        existing = Video.objects.filter(session=self.session, is_final=True).first()

        if existing:
            logger.info("Video already exists")
            return

        builder = TimelineBuilder(self.session)
        timeline = builder.build()

        dummy = Video(session=self.session, version=1)
        target_path = video_path(dummy, "video.mp4")

        job_id = self.ai.start_video_compose(timeline, output_path=target_path)

        video_file_path, duration = self.ai.wait_for_video(job_id)

        Video.objects.create(
            session=self.session,
            video_path=video_file_path,
            duration=duration,
            is_final=True,
        )

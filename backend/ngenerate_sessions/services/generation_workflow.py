import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from django.db import close_old_connections
from django.conf import settings

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
    video_path,
)

from ngenerate_sessions.models import (
    Sentence,
    Illustration,
    CharacterProfile,
    Character,
    GenerationRun,
)

from .ai_service import AIService
from .timeline_builder import TimelineBuilder
from .voice_mapper import VoiceMapper

logger = logging.getLogger(__name__)

MAX_IMAGE_WORKERS = getattr(settings, "GENERATION_MAX_IMAGE_WORKERS", 2)
MAX_VOICE_WORKERS = getattr(settings, "GENERATION_MAX_VOICE_WORKERS", 3)


def _with_db(fn):
    def wrapper(*args, **kwargs):
        close_old_connections()
        try:
            return fn(*args, **kwargs)
        finally:
            close_old_connections()

    return wrapper


def _run_parallel(fn, items, max_workers: int, label: str):
    errors = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_with_db(fn), item): item for item in items}
        try:
            for future in as_completed(futures):
                item = futures[future]
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"{label} failed | item={item} | {e}")
                    errors.append(e)
                    for f in futures:
                        f.cancel()
                    break
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
    if errors:
        raise errors[0]


class GenerationWorkflow:

    def __init__(self, generation_run: GenerationRun):

        self.run = generation_run
        self.session = generation_run.session
        self.ai = AIService()

    # =====================================================
    # MAIN WORKFLOW
    # =====================================================

    def run_workflow(self):
        logger.info(
            f"Start generation workflow | session={self.session.id} | run={self.run.id} | v{self.run.version}"
        )

        self.run.create_processing_steps()

        try:
            self._run_step(
                "Generating Character Master Image",
                self._generate_character_master,
            )

            self._run_parallel_phase_a()

            self._run_step(
                "Generating Character Emotion Image",
                self._generate_character_emotion,
            )

            self._run_step("Composite Video", self._compose_video)

        except Exception as e:
            logger.exception(
                f"Generation workflow failed | session={self.session.id} | run={self.run.id}"
            )
            raise

        logger.info(
            f"Generation workflow finished | session={self.session.id} | run={self.run.id}"
        )

        if self.run.status == "generating":
            self.run.complete()
        else:
            logger.warning(
                f"Skip complete | run={self.run.id} status={self.run.status}"
            )

    # ─────────────────────────────────────────────────────
    # HELPER: step marker — ใช้ GenerationProcessingStep
    # ─────────────────────────────────────────────────────
    def _run_step(self, step_name: str, fn):
        step = self.run.processing_steps.get(name=step_name)
        step.mark_start()
        try:
            fn()
            step.mark_success()
            self.run.update_notification_progress()
        except Exception as e:
            step.mark_failed(str(e))
            self.run.update_notification_progress()
            raise

    # ─────────────────────────────────────────────────────
    # Phase A-2: Scene + Voice พร้อมกัน
    # ─────────────────────────────────────────────────────
    def _run_parallel_phase_a(self):
        scene_step = self.run.processing_steps.get(name="Generating Scene Image")
        voice_step = self.run.processing_steps.get(name="Generating Narrator Voice")

        scene_step.mark_start()
        voice_step.mark_start()

        scene_error = None
        voice_error = None

        with ThreadPoolExecutor(max_workers=2) as executor:
            future_scene = executor.submit(_with_db(self._generate_scene))
            future_voice = executor.submit(_with_db(self._generate_voice))

            for future in as_completed([future_scene, future_voice]):
                try:
                    future.result()
                except Exception as e:
                    if future is future_scene:
                        scene_error = e
                    else:
                        voice_error = e

        if scene_error:
            scene_step.mark_failed(str(scene_error))
            self.run.update_notification_progress()
            raise scene_error

        if voice_error:
            voice_step.mark_failed(str(voice_error))
            self.run.update_notification_progress()
            raise voice_error

        scene_step.mark_success()
        voice_step.mark_success()
        self.run.update_notification_progress()

    # =====================================================
    # CHARACTER MASTER
    # =====================================================

    def _generate_character_master(self):
        profiles = list(
            CharacterProfile.objects.filter(characters__session=self.session).distinct()
        )

        def _one(profile):
            asset, _ = CharacterProfileAsset.objects.get_or_create(
                character_profile=profile
            )
            if asset.image and not asset.image.endswith("default_avatar.jpg"):
                return

            target_path = character_profile_asset_path(asset, "master.png")
            image_path = self.ai.generate_character_master(
                character_profile=profile,
                output_path=target_path,
                style=self.run.style,
            )
            asset.image = image_path
            asset.save()
            logger.info(f"Master image saved | profile={profile.id}")

        _run_parallel(_one, profiles, MAX_IMAGE_WORKERS, "Master image")

    # =====================================================
    # CHARACTER EMOTION IMAGE
    # =====================================================

    def _generate_character_emotion(self):
        characters = list(
            Character.objects.filter(session=self.session).select_related(
                "character_profile__asset",
                "illustration__chapter",
            )
        )

        def _one(character):

            if CharacterAsset.objects.filter(
                generation_run=self.run, character=character
            ).exists():
                return

            master_asset = getattr(character.character_profile, "asset", None)
            if not master_asset:
                raise Exception(
                    f"Master image missing for profile: {character.character_profile.id}"
                )


            dummy = CharacterAsset(
                generation_run=self.run,
                session=self.session,
                character=character,
            )
            output_path = character_asset_path(dummy, "emotion.png")

            image_path = self.ai.generate_character_emotion(
                character=character,
                reference_image_path=master_asset.image,
                output_path=output_path,
                style=self.run.style,
            )
            CharacterAsset.objects.create(
                generation_run=self.run,
                session=self.session,
                character=character,
                image=image_path,
            )
            logger.info(
                f"Emotion image saved | character={character.id} | {character.emotion}"
            )

        _run_parallel(_one, characters, MAX_IMAGE_WORKERS, "Emotion image")

    # =====================================================
    # SCENE IMAGE
    # =====================================================

    def _generate_scene(self):
        illustrations = list(Illustration.objects.filter(session=self.session))

        def _one(illustration):
            if IllustrationImage.objects.filter(
                generation_run=self.run, illustration=illustration
            ).exists():
                return

            dummy = IllustrationImage(
                generation_run=self.run,
                session=self.session,
                illustration=illustration,
            )
            output_path = illustration_image_path(dummy, "scene.png")

            image_path = self.ai.generate_scene_image(
                illustration=illustration,
                output_path=output_path,
                style=self.run.style,
            )
            IllustrationImage.objects.create(
                generation_run=self.run,
                session=self.session,
                illustration=illustration,
                image=image_path,
            )
            logger.info(f"Scene image saved | illustration={illustration.id}")

        _run_parallel(_one, illustrations, MAX_IMAGE_WORKERS, "Scene image")

    # =====================================================
    # VOICE
    # =====================================================

    def _generate_voice(self):
        sentences = list(
            Sentence.objects.filter(session=self.session)
            .select_related("chapter")
            .order_by("chapter__order", "sentence_index")
        )

        def _one(sentence):
            if NarratorVoice.objects.filter(
                generation_run=self.run, sentence=sentence
            ).exists():
                return

            voice_type, emotion, config = VoiceMapper.map(
                session=self.session,
                sentence=sentence,
            )
            dummy = NarratorVoice(
                generation_run=self.run,
                session=self.session,
                sentence=sentence,
            )
            output_path = narrator_voice_path(dummy, "voice.wav")

            tts_input = sentence.tts_text or sentence.sentence

            vpath, duration = self.ai.generate_voice_with_emotion(
                text=tts_input,
                voice_type=voice_type,
                emotion=emotion,
                output_path=output_path,
                **config,
            )
            NarratorVoice.objects.create(
                generation_run=self.run,
                session=self.session,
                sentence=sentence,
                voice=vpath,
                duration=duration,
            )
            logger.info(f"Voice saved | sentence_index={sentence.sentence_index}")

        _run_parallel(_one, sentences, MAX_VOICE_WORKERS, "Voice")

    # =====================================================
    # VIDEO COMPOSE
    # =====================================================

    def _compose_video(self):

        if hasattr(self.run, "video"):
            logger.info(f"Video already exists for run v{self.run.version}, skipping")
            return

        builder = TimelineBuilder(self.session, self.run)
        timeline = builder.build()

        dummy = Video(generation_run=self.run, session=self.session)
        target_path = video_path(dummy, "video.mp4")

        job_id = self.ai.start_video_compose(timeline, output_path=target_path)

        video_file_path, duration = self.ai.wait_for_video(job_id)
        close_old_connections()

        file_size = 0.0
        try:
            import os

            full_path = f"/workspace/ngenerate/{video_file_path}"
            if os.path.exists(full_path):
                file_size = round(os.path.getsize(full_path) / (1024 * 1024), 2)  # MB
        except Exception:
            pass

        Video.objects.create(
            generation_run=self.run,
            session=self.session,
            video_path=video_file_path,
            duration=duration,
            file_size=file_size,
            is_final=True,
        )
        logger.info(
            f"Video saved | session={self.session.id} | run=v{self.run.version} | duration={duration}"
        )

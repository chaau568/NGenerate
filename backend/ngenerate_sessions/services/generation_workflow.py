from asset.models import CharacterImage, CharacterVoice, IllustrationImage
from ngenerate_sessions.models import Sentence, Illustration, Character
from .ai_service import AIService
from .timeline_builder import TimelineBuilder
from .video_composer import VideoComposer


class GenerationWorkflow:

    def __init__(self, session):
        self.session = session
        self.novel = session.novel
        self.ai = AIService()  # ✅ ใช้ facade ตัวเดียว

    # =====================================================
    # MAIN ENTRY
    # =====================================================

    def run(self):

        self.session.create_processing_steps("generation")

        while True:
            step = self.session.get_next_pending_step("generation")

            if not step:
                break

            try:
                step.mark_start()

                if step.name == "Character Image Generation":
                    self._run_character_image_generation()

                elif step.name == "Scene Image Generation":
                    self._run_scene_generation()

                elif step.name == "Voice Generation":
                    self._run_voice_generation()
                    
                elif step.name == "Video Composition":
                    self._run_video_composition()

                step.mark_success()
                self.session.update_notification_progress()

            except Exception as e:
                step.mark_failed(str(e))
                self.session.update_notification_progress()
                raise

        self.session.complete_generation()

    # =====================================================
    # CHARACTER IMAGE
    # =====================================================

    def _run_character_image_generation(self):

        characters = (
            Character.objects
            .filter(sentences__session=self.session)
            .distinct()
        )

        for character in characters:

            # ✅ ถ้ามีแล้วข้าม
            if CharacterImage.objects.filter(
                session=self.session,
                character=character
            ).exists():
                continue

            image_file = self.ai.generate_character_image(
                character=character,
                session=self.session
            )

            CharacterImage.objects.create(
                session=self.session,
                character=character,
                image=image_file
            )

    # =====================================================
    # SCENE IMAGE
    # =====================================================

    def _run_scene_generation(self):

        illustrations = Illustration.objects.filter(
            session=self.session
        )

        for illustration in illustrations:

            if IllustrationImage.objects.filter(
                session=self.session,
                illustration=illustration
            ).exists():
                continue

            image_file = self.ai.generate_scene_image(
                illustration=illustration,
                session=self.session
            )

            IllustrationImage.objects.create(
                session=self.session,
                illustration=illustration,
                image=image_file
            )

    # =====================================================
    # VOICE
    # =====================================================

    def _run_voice_generation(self):

        sentences = (
            Sentence.objects
            .filter(session=self.session)
            .select_related("character")
        )

        for sentence in sentences:

            # narration ไม่ต้อง generate
            if sentence.type != "dialogue":
                continue

            if CharacterVoice.objects.filter(
                session=self.session,
                sentence=sentence
            ).exists():
                continue

            audio_file, duration = self.ai.generate_voice(
                sentence=sentence
            )

            CharacterVoice.objects.create(
                session=self.session,
                sentence=sentence,
                voice=audio_file,
                duration=duration
            )
            
    # =====================================================
    # VOICE
    # =====================================================
            
    def _run_video_composition(self):

        builder = TimelineBuilder(self.session)
        timeline = builder.build()

        composer = VideoComposer(
            timeline=timeline,
            output_dir="/tmp"
        )

        final_video_path = composer.compose()

        self.session.video_file = final_video_path
        self.session.save()
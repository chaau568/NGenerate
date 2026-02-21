from django.conf import settings
from ngenerate_sessions.models import CharacterProfile, Sentence, Illustration, Character
from .character_profile_analysis import CharacterProfileAnalysis
from .scene_analysis import SceneAnalysis
from .sentence_analysis import StoryPipeline


class AnalysisWorkflow:

    def __init__(self, session):
        self.session = session
        self.novel = session.novel
        self.chapters = session.chapters.all()

        self.ollama_url = settings.OLLAMA_URL
        self.llama_model = settings.LLAMA_MODEL
        self.timeout = settings.TIMEOUT

    # =====================================================

    def run(self):

        self.session.create_processing_steps("analysis")

        while True:
            step = self.session.get_next_pending_step("analysis")

            if not step:
                break

            try:
                step.mark_start()

                if step.name == "Character Identification":
                    self._run_character_analysis()

                elif step.name == "Scene Segmentation":
                    self._run_scene_analysis()

                elif step.name == "Sentence Structuring":
                    self._run_sentence_analysis()

                step.mark_success()
                self.session.update_notification_progress()

            except Exception as e:
                step.mark_failed(str(e))
                self.session.update_notification_progress()
                self.session.fail(str(e))
                return

        self.session.complete_analysis()

    # =====================================================
    # CHARACTER
    # =====================================================

    def _run_character_analysis(self):

        analyzer = CharacterProfileAnalysis(
            self.ollama_url,
            self.llama_model,
            self.timeout
        )

        existing_profiles = list(
            self.novel.character_profiles.values(
                "name",
                "appearance",
                "outfit",
                "sex",
                "age",
                "race",
                "base_personality"
            )
        )

        for chapter in self.chapters:

            result = analyzer.run(
                story_text=chapter.story,
                existing_profiles=existing_profiles
            )

            for data in result.get("character_profile", []):
                CharacterProfile.objects.update_or_create(
                    novel=self.novel,
                    name=data["name"],
                    defaults=data
                )

    # =====================================================
    # SCENE
    # =====================================================

    def _run_scene_analysis(self):

        analyzer = SceneAnalysis(
            self.ollama_url,
            self.llama_model,
            self.timeout
        )

        for chapter in self.chapters:

            result = analyzer.analyze_master_scene(
                chapter_text=chapter.story,
                style=self.session.style
            )

            Illustration.objects.update_or_create(
                session=self.session,
                chapter=chapter,
                defaults=result
            )

    # =====================================================
    # SENTENCE
    # =====================================================

    def _run_sentence_analysis(self):

        pipeline = StoryPipeline(
            self.ollama_url,
            self.llama_model,
            self.timeout
        )

        Sentence.objects.filter(session=self.session).delete()

        character_profiles = list(
            self.novel.character_profiles.values(
                "name",
                "appearance",
                "outfit",
                "sex",
                "age",
                "race",
                "base_personality"
            )
        )

        for chapter in self.chapters:

            analyzed = pipeline.process(
                story_text=chapter.story,
                character_profiles=character_profiles
            )

            for data in analyzed:

                character_instance = self._resolve_character(
                    data["speaker"],
                    data["emotion"]
                )

                Sentence.objects.create(
                    session=self.session,
                    chapter=chapter,
                    sentence_index=data["sentence_index"],
                    sentence=data["text"],
                    type=data["type"],
                    emotion=data["emotion"],
                    character=character_instance
                )

    # =====================================================
    # RESOLVE CHARACTER FK
    # =====================================================

    def _resolve_character(self, speaker_name, emotion):

        if speaker_name in ["unknown", "narrator"]:
            return None

        try:
            profile = CharacterProfile.objects.get(
                novel=self.novel,
                name=speaker_name
            )

            character, _ = Character.objects.get_or_create(
                profile=profile,
                emotion=emotion,
                defaults={
                    "positive_prompt": "",
                    "negative_prompt": ""
                }
            )

            return character

        except CharacterProfile.DoesNotExist:
            return None
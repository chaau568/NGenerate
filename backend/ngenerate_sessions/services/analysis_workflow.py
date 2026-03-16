from django.conf import settings
from django.db import transaction
from ngenerate_sessions.models import (
    CharacterProfile,
    Sentence,
    Illustration,
    SentenceCharacter,
    Character,
)

from .character_profile_analysis import CharacterProfileAnalysis
from .character_generate_prompt import GenerateCharacterPrompt
from .scene_analysis import SceneAnalysis
from .convert import ConvertTextToJson
from .emotion_detect_analysis import EmotionAnalysis
from .display_character_analysis import DisplayCharacterAnalysis


class AnalysisWorkflow:

    def __init__(self, session):
        self.session = session
        self.novel = session.novel
        self.chapters = session.chapters.all().order_by("order")

        self.ai_api_url = settings.AI_API_URL
        self.timeout = settings.AI_TIMEOUT

        self.EMOTION_MAP = {
            "happy": "smiling",
            "sad": "crying",
            "angry": "angry face",
            "serious": "serious face",
            "neutral": "neutral face",
        }

    # =========================================================
    # MAIN RUN
    # =========================================================
    def run(self):

        self.session.create_processing_steps("analysis")

        try:

            # STEP 1
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Character"
            )
            step.mark_start()

            for chapter in self.chapters:
                self._analyze_characters(chapter)

            step.mark_success()
            self.session.update_notification_progress()

            # STEP 2
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Sentence"
            )
            step.mark_start()

            for chapter in self.chapters:
                self._analyze_sentences_pipeline(chapter)

            step.mark_success()
            self.session.update_notification_progress()

            # STEP 3
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Scene"
            )
            step.mark_start()

            for chapter in self.chapters:
                self._analyze_scene(chapter)

            step.mark_success()
            self.session.update_notification_progress()

            self.session.complete_analysis()

        except Exception as e:
            if "step" in locals():
                step.mark_failed(str(e))
            self.session.fail(str(e))
            raise e

    # =========================================================
    # CHARACTER ANALYSIS
    # =========================================================
    def _analyze_characters(self, chapter):

        analyzer = CharacterProfileAnalysis(
            self.ai_api_url,
            self.timeout,
        )

        generator = GenerateCharacterPrompt(
            self.ai_api_url,
            self.timeout,
        )

        result = analyzer.run(story_text=chapter.story)

        for data in result.get("character_profile", []):

            profile, created = CharacterProfile.objects.get_or_create(
                novel=self.novel,
                name=data["name"],
                defaults={
                    "sex": data.get("sex", ""),
                    "race": data.get("race", ""),
                    "age": data.get("age", ""),
                    "appearance": data.get("appearance", ""),
                    "outfit": data.get("outfit", ""),
                    "base_personality": data.get("base_personality", ""),
                },
            )

            if not created:

                if data.get("age"):
                    profile.age = data["age"]

                if data.get("appearance"):
                    profile.appearance = data["appearance"]

                if data.get("outfit"):
                    profile.outfit = data["outfit"]

                if data.get("sex"):
                    profile.sex = data["sex"]

                if data.get("race"):
                    profile.race = data["race"]

                if data.get("base_personality"):
                    profile.base_personality = data["base_personality"]

            character_data = {
                "name": profile.name,
                "appearance": profile.appearance,
                "outfit": profile.outfit,
                "sex": profile.sex,
                "age": profile.age,
                "race": profile.race,
                "base_personality": profile.base_personality,
            }

            result_prompt = generator.generate_prompt(
                character_profile_data=character_data,
                style=self.session.style,
            )

            profile.positive_prompt = result_prompt.get("positive_prompt", "")
            profile.negative_prompt = result_prompt.get("negative_prompt", "")

            profile.save()

    # =========================================================
    # SENTENCE PIPELINE
    # =========================================================
    def _analyze_sentences_pipeline(self, chapter):
        converter = ConvertTextToJson()
        emotion_analyzer = EmotionAnalysis(self.ai_api_url, self.timeout)

        display_analyzer = DisplayCharacterAnalysis(self.ai_api_url, self.timeout)

        story_json = converter.text_file_to_json(chapter.story)
        emotion_results = emotion_analyzer.run(story_json)
        emotion_map = {
            item["sentence_index"]: item["emotion"] for item in emotion_results
        }

        character_profiles_list = list(self.novel.character_profiles.values("name"))
        display_result = display_analyzer.run(story_json, character_profiles_list)

        display_map = {}
        for item in display_result["display_characters"]:
            for idx in item["sentence_index_range"]:
                display_map.setdefault(idx, []).append(item["name"])

        character_map = {
            c.name: c for c in CharacterProfile.objects.filter(novel=self.novel)
        }

        with transaction.atomic():
            Sentence.objects.filter(session=self.session, chapter=chapter).delete()

            for s in story_json["sentences"]:
                idx = s["sentence_index"]
                current_emotion = emotion_map.get(idx, "neutral")

                sentence_obj = Sentence.objects.create(
                    session=self.session,
                    chapter=chapter,
                    sentence_index=idx,
                    sentence=s["text"],
                    emotion=current_emotion,
                )

                for name in display_map.get(idx, []):

                    profile = character_map.get(name)

                    if not profile:
                        continue

                    char_obj = self._get_character_emotion_prompt(
                        chapter, profile, current_emotion
                    )

                    SentenceCharacter.objects.get_or_create(
                        sentence=sentence_obj,
                        character=char_obj,
                    )

    # =========================================================
    # SCENE ANALYSIS
    # =========================================================
    def _analyze_scene(self, chapter):

        analyzer = SceneAnalysis(
            self.ai_api_url,
            self.timeout,
        )

        result = analyzer.analyze_master_scene(
            chapter_text=chapter.story,
            style=self.session.style,
        )

        Illustration.objects.update_or_create(
            session=self.session,
            chapter=chapter,
            defaults=result,
        )

    # =========================================================
    # GENERATE SENTENCE CHARACTER PROMPT
    # =========================================================

    def _get_character_emotion_prompt(self, chapter, profile, emotion):
        emotion_modifier = self.EMOTION_MAP.get(emotion, "")
        base_positive = profile.positive_prompt
        base_negative = profile.negative_prompt

        positive_prompt = (
            f"{base_positive}, {emotion_modifier}"
            if emotion_modifier
            else base_positive
        )

        char_obj, _ = Character.objects.get_or_create(
            session=self.session,
            chapter=chapter,
            character_profile=profile,
            emotion=emotion,
            defaults={
                "positive_prompt": positive_prompt,
                "negative_prompt": base_negative,
            },
        )

        return char_obj

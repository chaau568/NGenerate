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
    """
    Analysis Workflow

    ลำดับการทำงานต่อ chapter:
    ──────────────────────────────────────────────
    STEP 1  แบ่งประโยค — global index ต่อเนื่องทั้ง session
    STEP 2  วิเคราะห์ตัวละคร — 2-pass (detect → describe)
            + สร้าง appearance anchor prompt
    STEP 3  วิเคราะห์ scene — LLM แบ่ง scene boundaries
            + สร้าง scene background prompt
    STEP 4  Emotion + Display character per sentence
            + สร้าง Character per (illustration, profile, emotion)
              โดย outfit/pose มาจาก scene_description ของ illustration นั้น
    """

    def __init__(self, session):
        self.session = session
        self.novel = session.novel
        self.chapters = session.chapters.all().order_by("order")

        self.ai_api_url = settings.AI_API_URL
        self.timeout = settings.AI_TIMEOUT

    # =========================================================
    # MAIN RUN
    # =========================================================

    def run(self):

        self.session.create_processing_steps("analysis")

        global_sentence_index = 1

        try:
            # ─────────────────────────────────────────────
            # STEP 1 — แบ่งประโยค
            # ─────────────────────────────────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Sentence"
            )
            step.mark_start()

            chapter_sentences: dict[int, list] = {}

            for chapter in self.chapters:
                result = self._split_sentences(chapter, global_sentence_index)
                chapter_sentences[chapter.id] = result["sentences"]
                global_sentence_index = result["next_index"]

            step.mark_success()
            self.session.update_notification_progress()

            # ─────────────────────────────────────────────
            # STEP 2 — วิเคราะห์ตัวละคร + appearance anchor
            # ─────────────────────────────────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Character"
            )
            step.mark_start()

            for chapter in self.chapters:
                self._analyze_characters(chapter)

            step.mark_success()
            self.session.update_notification_progress()

            # ─────────────────────────────────────────────
            # STEP 3 — วิเคราะห์ scene
            # ─────────────────────────────────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Analysis Scene"
            )
            step.mark_start()

            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_scenes(chapter, sentences)

            step.mark_success()
            self.session.update_notification_progress()

            # ─────────────────────────────────────────────
            # STEP 4 — emotion + display + character per scene
            # ─────────────────────────────────────────────
            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_sentence_pipeline(chapter, sentences)

            self.session.complete_analysis()

        except Exception as e:
            if "step" in locals():
                step.mark_failed(str(e))
            self.session.fail(str(e))
            raise e

    # =========================================================
    # STEP 1: SPLIT SENTENCES (global index)
    # =========================================================

    def _split_sentences(self, chapter, start_index: int) -> dict:
        converter = ConvertTextToJson()
        result = converter.text_to_json(chapter.story, start_index=start_index)

        with transaction.atomic():
            Sentence.objects.filter(session=self.session, chapter=chapter).delete()
            Sentence.objects.bulk_create(
                [
                    Sentence(
                        session=self.session,
                        chapter=chapter,
                        sentence_index=s["sentence_index"],
                        sentence=s["text"],
                        tts_text=s.get("tts_text", ""),
                        emotion="neutral",
                    )
                    for s in result["sentences"]
                ]
            )

        return result  # {"sentences": [...], "next_index": N}

    # =========================================================
    # STEP 2: CHARACTER ANALYSIS — APPEARANCE ANCHOR ONLY
    # =========================================================

    def _analyze_characters(self, chapter):
        """
        3-pass character analysis + สร้าง appearance anchor

        ใช้ alias_map จาก CharacterProfileAnalysis เพื่อ:
        - merge ตัวละครที่ชื่อต่างกันแต่คนเดียวกัน
        - เก็บ aliases ใน CharacterProfile เพื่อให้ display_character_analysis
          match ชื่อได้ครบ
        """
        analyzer = CharacterProfileAnalysis(self.ai_api_url, self.timeout)
        generator = GenerateCharacterPrompt(self.ai_api_url, self.timeout)

        result = analyzer.run(story_text=chapter.story)
        alias_map = result.get("alias_map", {})  # {canonical: [alias1, alias2]}

        for data in result.get("character_profile", []):

            profile, created = CharacterProfile.objects.get_or_create(
                novel=self.novel,
                name=data["name"],
                defaults={
                    "sex": data.get("sex", "man"),
                    "race": data.get("race", "human"),
                    "age": data.get("age", "adult"),
                    "appearance": data.get("appearance", ""),
                    "outfit": data.get("outfit", ""),
                    "base_personality": data.get("base_personality", ""),
                },
            )

            if not created:
                updated = False
                for field in [
                    "age",
                    "appearance",
                    "outfit",
                    "sex",
                    "race",
                    "base_personality",
                ]:
                    val = data.get(field, "").strip()
                    if val and val not in {
                        "not described",
                        "simple casual clothing",
                        "neutral",
                        "human",
                    }:
                        setattr(profile, field, val)
                        updated = True
                if updated:
                    profile.save()

            # เก็บ aliases ใน profile เพื่อให้ display_character_analysis
            # สามารถ match ชื่อได้ครบทุก alias
            aliases = alias_map.get(data["name"], [])
            if aliases:
                existing_aliases = set(
                    profile.aliases.split(",") if profile.aliases else []
                )
                new_aliases = existing_aliases | set(aliases)
                new_aliases.discard("")
                profile.aliases = ",".join(sorted(new_aliases))
                profile.save(update_fields=["aliases"])

            character_data = {
                "name": profile.name,
                "appearance": profile.appearance,
                "outfit": profile.outfit,
                "sex": profile.sex,
                "age": profile.age,
                "race": profile.race,
                "base_personality": profile.base_personality,
            }

            anchor = generator.generate_appearance_anchor(
                character_profile_data=character_data,
                style=self.session.style,
            )

            profile.positive_prompt = anchor["positive_prompt"]
            profile.negative_prompt = anchor["negative_prompt"]
            profile.appearance_tags = anchor.get("_appearance_tags", "")
            profile.save()

    # =========================================================
    # STEP 3: SCENE ANALYSIS — หลาย scenes ต่อ chapter
    # =========================================================

    def _analyze_scenes(self, chapter, sentences: list):
        analyzer = SceneAnalysis(self.ai_api_url, self.timeout)

        scene_results = analyzer.analyze_chapter_scenes(
            chapter_text=chapter.story,
            sentences=sentences,
            style=self.session.style,
        )

        Illustration.objects.filter(session=self.session, chapter=chapter).delete()

        Illustration.objects.bulk_create(
            [
                Illustration(
                    session=self.session,
                    chapter=chapter,
                    scene_index=scene["scene_index"],
                    sentence_start=scene["sentence_start"],
                    sentence_end=scene["sentence_end"],
                    scene_description=scene.get("scene_description", ""),
                    positive_prompt=scene["positive_prompt"],
                    negative_prompt=scene["negative_prompt"],
                )
                for scene in scene_results
            ]
        )

        print(f"✅ Ch{chapter.order}: {len(scene_results)} scenes")

    # =========================================================
    # STEP 4: EMOTION + DISPLAY + CHARACTER PER SCENE
    # =========================================================

    def _analyze_sentence_pipeline(self, chapter, sentences: list):

        emotion_analyzer = EmotionAnalysis(self.ai_api_url, self.timeout)
        display_analyzer = DisplayCharacterAnalysis(self.ai_api_url, self.timeout)

        story_json = {"sentences": sentences}

        # Emotion per sentence
        emotion_results = emotion_analyzer.run(story_json)
        emotion_map = {
            item["sentence_index"]: item["emotion"] for item in emotion_results
        }

        # Display characters per sentence
        character_profiles_list = list(self.novel.character_profiles.values("name"))
        display_result = display_analyzer.run(story_json, character_profiles_list)

        display_map: dict[int, list] = {}
        for item in display_result["display_characters"]:
            for idx in item["sentence_index_range"]:
                display_map.setdefault(idx, []).append(item["name"])

        character_map = {
            c.name: c for c in CharacterProfile.objects.filter(novel=self.novel)
        }

        # โหลด Illustration ของ chapter นี้ พร้อม lookup sentence_index → illustration
        illustration_lookup = self._build_illustration_lookup(chapter)

        # cache: (illustration_id, profile_id, emotion) → Character
        # เพื่อไม่ให้ generate prompt ซ้ำในประโยคอื่นของ scene เดียวกัน
        char_cache: dict[tuple, Character] = {}

        with transaction.atomic():

            sentence_objects = {
                s.sentence_index: s
                for s in Sentence.objects.filter(session=self.session, chapter=chapter)
            }

            for s_data in sentences:
                idx = s_data["sentence_index"]
                sentence_obj = sentence_objects.get(idx)
                if not sentence_obj:
                    continue

                emotion = emotion_map.get(idx, "neutral")
                sentence_obj.emotion = emotion
                sentence_obj.save(update_fields=["emotion"])

                illustration = illustration_lookup.get(idx)
                if not illustration:
                    continue

                for name in display_map.get(idx, []):
                    profile = character_map.get(name)
                    if not profile:
                        continue

                    cache_key = (illustration.id, profile.id, emotion)

                    if cache_key not in char_cache:
                        char_obj = self._get_or_create_character(
                            illustration=illustration,
                            profile=profile,
                            emotion=emotion,
                        )
                        char_cache[cache_key] = char_obj

                    SentenceCharacter.objects.get_or_create(
                        sentence=sentence_obj,
                        character=char_cache[cache_key],
                    )

    # =========================================================
    # HELPER: ILLUSTRATION LOOKUP
    # =========================================================

    def _build_illustration_lookup(self, chapter) -> dict[int, Illustration]:
        illustrations = Illustration.objects.filter(
            session=self.session, chapter=chapter
        ).order_by("scene_index")

        result: dict[int, Illustration] = {}

        for illus in illustrations:
            s_start = illus.sentence_start or 0
            s_end = illus.sentence_end or 0
            for idx in range(s_start, s_end + 1):
                result[idx] = illus

        return result

    # =========================================================
    # HELPER: GET OR CREATE CHARACTER (PER SCENE)
    # =========================================================

    def _get_or_create_character(
        self,
        illustration: Illustration,
        profile: CharacterProfile,
        emotion: str,
    ) -> Character:
        existing = Character.objects.filter(
            session=self.session,
            illustration=illustration,
            character_profile=profile,
            emotion=emotion,
        ).first()

        if existing:
            return existing

        generator = GenerateCharacterPrompt(self.ai_api_url, self.timeout)

        appearance_anchor = (
            profile.appearance_tags or profile.appearance or "simple anime character"
        )
        identity = generator._resolve_identity(profile.sex, profile.age)

        scene_prompt = generator.generate_scene_prompt(
            appearance_anchor=appearance_anchor,
            identity=identity,
            scene_description=illustration.scene_description,
            character_name=profile.name,
            emotion=emotion,
            style=self.session.style,
        )

        char_obj = Character.objects.create(
            session=self.session,
            illustration=illustration,
            character_profile=profile,
            emotion=emotion,
            positive_prompt=scene_prompt["positive_prompt"],
            negative_prompt=scene_prompt["negative_prompt"],
        )

        return char_obj

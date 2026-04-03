import re

from django.conf import settings
from django.db import transaction

from ngenerate_sessions.models import (
    CharacterProfile,
    Sentence,
    Illustration,
    SceneCharacter,
)

from .character_profile_analysis import CharacterProfileAnalysis
from .character_generate_prompt import GenerateCharacterPrompt
from .scene_analysis import SceneAnalysis
from .scene_character_analysis import SceneCharacterAnalysis
from .convert import ConvertTextToJson


class AnalysisWorkflow:
    """
    Analysis Workflow

    ลำดับการทำงาน:
    ──────────────────────────────────────────────
    STEP 1  แบ่งประโยค — global index ต่อเนื่องทั้ง session

    STEP 2  วิเคราะห์ตัวละคร — 3-pass บน full text ของทุก chapter รวมกัน
            (detect names → dedup/filter → describe)
            *** ไม่มี alias map ***

    STEP 3  วิเคราะห์ scene — แบ่ง scene boundaries + สร้าง background prompt

    STEP 4  วิเคราะห์ SceneCharacter ต่อ scene
            — pass character_names list เข้าไป ให้ LLM ระบุตัวละครในฉากโดยตรง
    ──────────────────────────────────────────────
    """

    def __init__(self, session):
        self.session = session
        self.novel = session.novel
        self.chapters = list(session.chapters.all().order_by("order"))

        self.ai_api_url = settings.AI_API_URL
        self.timeout = settings.AI_TIMEOUT

    # =========================================================
    # MAIN RUN
    # =========================================================

    def run(self):
        self.session.create_processing_steps("analysis")

        global_sentence_index = 1

        try:
            # ── STEP 1: Split Sentences ──────────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Split Sentences"
            )
            step.mark_start()

            chapter_sentences: dict[int, list] = {}
            for chapter in self.chapters:
                result = self._split_sentences(chapter, global_sentence_index)
                chapter_sentences[chapter.id] = result["sentences"]
                global_sentence_index = result["next_index"]

            step.mark_success()
            self.session.update_notification_progress()

            # ── STEP 2: Identify Characters ──────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Identify Characters"
            )
            step.mark_start()

            # รวม full text ของทุก chapter เข้าด้วยกัน
            full_story_text = "\n\n".join(
                chapter.story for chapter in self.chapters if chapter.story
            )

            self._analyze_characters(full_story_text)

            step.mark_success()
            self.session.update_notification_progress()

            # ── STEP 3: Segment Scenes ────────────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Segment Scenes"
            )
            step.mark_start()

            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_scenes(chapter, sentences)

            step.mark_success()
            self.session.update_notification_progress()

            # ── STEP 4: Analyze Scene Characters ─────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Analyze Sentence Details"
            )
            step.mark_start()

            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_scene_characters(chapter, sentences)

            step.mark_success()
            self.session.update_notification_progress()

            # ── STEP 5: Build Base Structure ──────────────────
            step = self.session.processing_steps.get(
                phase="analysis", name="Build Base Structure"
            )
            step.mark_start()
            self.session.complete_analysis()
            step.mark_success()

        except Exception as e:
            if "step" in locals():
                step.mark_failed(str(e))
            self.session.fail(str(e))
            raise e

    # =========================================================
    # STEP 1: SPLIT SENTENCES
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
                    )
                    for s in result["sentences"]
                ]
            )

        return result

    # =========================================================
    # STEP 2: CHARACTER ANALYSIS (ไม่มี alias)
    # =========================================================

    def _analyze_characters(self, full_story_text: str):
        analyzer = CharacterProfileAnalysis(self.ai_api_url, self.timeout)
        generator = GenerateCharacterPrompt(self.ai_api_url, self.timeout)

        result = analyzer.run(story_text=full_story_text)
        profiles_data = result.get("character_profile", [])

        print(f"   📋 Total canonical characters: {len(profiles_data)}")
        self._save_character_profiles(profiles_data, generator)

    # =========================================================
    # SAVE CHARACTER PROFILES (ไม่มี alias_map)
    # =========================================================

    def _save_character_profiles(
        self,
        profiles_data: list,
        generator: GenerateCharacterPrompt,
    ):
        DEFAULT_VALS = {
            "not described",
            "simple casual clothing",
            "neutral",
            "human",
            "adult",
            "man",
            "woman",
        }

        for data in profiles_data:
            name = data.get("name", "").strip()
            if not name:
                continue

            profile, created = CharacterProfile.objects.get_or_create(
                novel=self.novel,
                name=name,
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
                    if val and val not in DEFAULT_VALS:
                        setattr(profile, field, val)
                        updated = True
                if updated:
                    profile.save()

            if profile.aliases:
                profile.aliases = ""
                profile.save(update_fields=["aliases"])

            anchor = generator.generate_appearance_anchor(
                character_profile_data={
                    "name": profile.name,
                    "appearance": profile.appearance,
                    "outfit": profile.outfit,
                    "sex": profile.sex,
                    "age": profile.age,
                    "race": profile.race,
                    "base_personality": profile.base_personality,
                },
                style=self.session.style,
            )

            profile.positive_prompt = anchor["positive_prompt"]
            profile.negative_prompt = anchor["negative_prompt"]
            profile.appearance_tags = anchor.get("_appearance_tags", "")
            profile.save()

            print(f"✅ {name} saved (sex={profile.sex}, age={profile.age})")

    # =========================================================
    # STEP 3: SCENE ANALYSIS
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
    # STEP 4: SCENE CHARACTER ANALYSIS
    # =========================================================

    def _analyze_scene_characters(self, chapter, sentences: list):
        scene_analyzer = SceneCharacterAnalysis(self.ai_api_url, self.timeout)
        prompt_generator = GenerateCharacterPrompt(self.ai_api_url, self.timeout)

        illustrations = Illustration.objects.filter(
            session=self.session, chapter=chapter
        ).order_by("scene_index")

        if not illustrations.exists():
            return

        sent_text_map = {s["sentence_index"]: s["text"] for s in sentences}

        profiles = list(CharacterProfile.objects.filter(novel=self.novel))
        profile_map = self._build_profile_map(profiles)
        all_known_names = [p.name for p in profiles]

        SceneCharacter.objects.filter(
            session=self.session,
            illustration__chapter=chapter,
        ).delete()

        for illustration in illustrations:
            s_start = illustration.sentence_start or 0
            s_end = illustration.sentence_end or 0

            context_start = max(0, s_start - 2)
            scene_sentences = []
            for idx in range(context_start, s_end + 1):
                if idx in sent_text_map:
                    scene_sentences.append(sent_text_map[idx])

            if not scene_sentences:
                continue

            print(
                f"🎬 Ch{chapter.order} Scene{illustration.scene_index} "
                f"(s{s_start}-s{s_end}): analyzing characters..."
            )

            char_results = scene_analyzer.analyze(
                sentences=scene_sentences,
                character_names=all_known_names,
                scene_description=illustration.scene_description,
            )

            print(
                f"👤 Scene characters: "
                f"{[(c['name'], c.get('action', '-')) for c in char_results]}"
            )

            scene_char_objs = []
            seen_profiles = set()

            for char_data in char_results:
                name_raw = char_data["name"]
                profile = self._resolve_profile(name_raw, profile_map)

                if not profile:
                    print(f"   ❌ Cannot resolve character: '{name_raw}'")
                    continue

                if profile.id in seen_profiles:
                    print(f"   ⚠️  Duplicate profile skipped: '{profile.name}'")
                    continue
                seen_profiles.add(profile.id)

                appearance_anchor = (
                    profile.appearance_tags
                    or profile.appearance
                    or "simple anime character"
                )
                identity = prompt_generator._resolve_identity(profile.sex, profile.age)

                scene_context = self._build_scene_context(
                    scene_description=illustration.scene_description,
                    pose=char_data.get("pose", "standing"),
                    action=char_data.get("action", ""),
                    expression=char_data.get("expression", "neutral"),
                )

                char_prompt = prompt_generator.generate_scene_prompt(
                    appearance_anchor=appearance_anchor,
                    identity=identity,
                    scene_description=scene_context,
                    character_name=profile.name,
                    scene_character=char_data,
                    style=self.session.style,
                )

                scene_char_objs.append(
                    SceneCharacter(
                        session=self.session,
                        illustration=illustration,
                        character_profile=profile,
                        pose=char_data.get("pose", "standing"),
                        action=char_data.get("action", ""),
                        expression=char_data.get("expression", "neutral"),
                        positive_prompt=char_prompt["positive_prompt"],
                        negative_prompt=char_prompt["negative_prompt"],
                    )
                )

            if scene_char_objs:
                SceneCharacter.objects.bulk_create(
                    scene_char_objs,
                    ignore_conflicts=True,
                )
                print(
                    f"✅ Saved {len(scene_char_objs)} SceneCharacter(s): "
                    f"{[(obj.character_profile.name, obj.action) for obj in scene_char_objs]}"
                )
            else:
                print(f"⚠️  No SceneCharacter saved for Scene{illustration.scene_index}")

    # =========================================================
    # HELPERS
    # =========================================================

    def _normalize_name(self, name: str) -> str:
        import unicodedata

        name = unicodedata.normalize("NFC", name.strip().lower())
        name = re.sub(r"\s+", "", name)
        return name

    def _build_profile_map(
        self, profiles: list[CharacterProfile]
    ) -> dict[str, CharacterProfile]:
        """
        สร้าง lookup map: normalized_name → CharacterProfile
        ไม่มี alias แล้ว — map จาก profile.name เท่านั้น
        """
        result: dict[str, CharacterProfile] = {}
        for profile in profiles:
            result[self._normalize_name(profile.name)] = profile
        return result

    def _resolve_profile(
        self, name_raw: str, profile_map: dict
    ) -> CharacterProfile | None:
        """
        Resolve ชื่อจาก LLM → CharacterProfile
        1. exact match (normalized)
        2. fuzzy match (threshold 0.75)
        """
        import difflib

        name = self._normalize_name(name_raw)

        if name in profile_map:
            return profile_map[name]

        best_match = None
        best_score = 0.0
        for key, profile in profile_map.items():
            score = difflib.SequenceMatcher(None, name, key).ratio()
            if score > best_score:
                best_score = score
                best_match = profile

        if best_score > 0.75:
            print(
                f"   🔍 Fuzzy match: '{name_raw}' → '{best_match.name}' ({best_score:.2f})"
            )
            return best_match

        return None

    def _build_scene_context(
        self,
        scene_description: str,
        pose: str,
        action: str,
        expression: str,
    ) -> str:
        parts = [scene_description]
        if pose:
            parts.append(f"pose: {pose}")
        if action:
            parts.append(f"action: {action}")
        if expression:
            parts.append(f"expression: {expression}")
        return ", ".join(parts)

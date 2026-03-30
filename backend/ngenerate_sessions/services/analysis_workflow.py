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

    ลำดับการทำงานต่อ chapter:
    ──────────────────────────────────────────────
    STEP 1  แบ่งประโยค — global index ต่อเนื่องทั้ง session

    STEP 2  วิเคราะห์ตัวละคร — 3-pass (detect → dedup → describe)
            + สร้าง appearance anchor prompt
            ส่งเป็น chunk ๆ ละ CHAR_CHUNK_SIZE ประโยค

    STEP 3  วิเคราะห์ scene — แบ่ง scene boundaries
            + สร้าง background prompt ต่อ scene

    STEP 4  วิเคราะห์ SceneCharacter ต่อ scene
            — ตัวละครคนไหนปรากฏ + pose/action/expression
            + สร้าง character prompt ต่อ (illustration, character_profile)
    ──────────────────────────────────────────────
    """

    CHAR_CHUNK_SIZE = 40

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

            step = self.session.processing_steps.get(
                phase="analysis", name="Identify Characters"
            )
            step.mark_start()

            all_sentences = []
            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                all_sentences.extend(sentences)

            self._analyze_characters(all_sentences)

            step.mark_success()
            self.session.update_notification_progress()

            step = self.session.processing_steps.get(
                phase="analysis", name="Segment Scenes"
            )
            step.mark_start()

            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_scenes(chapter, sentences)

            step.mark_success()
            self.session.update_notification_progress()

            step = self.session.processing_steps.get(
                phase="analysis", name="Analyze Sentence Details"
            )
            step.mark_start()

            for chapter in self.chapters:
                sentences = chapter_sentences[chapter.id]
                self._analyze_scene_characters(chapter, sentences)

            step.mark_success()
            self.session.update_notification_progress()

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
    # STEP 2: CHARACTER ANALYSIS
    #
    # แก้ปัญหา: alias ของ canonical ในช่วงหลัง อาจถูก detect เป็น
    # canonical แยกในช่วงแรก ทำให้เกิด profile ซ้ำซ้อน
    #
    # วิธีแก้: หลังรวบรวม all_profiles และ all_alias_map จากทุก chunk แล้ว
    # ให้ทำ "canonical merge pass" — ถ้าชื่อ A อยู่ใน all_profiles
    # แต่ก็เป็น alias ของ B ด้วย → merge ข้อมูลของ A เข้า B แล้วลบ A ออก
    # =========================================================

    def _analyze_characters(self, sentences: list):
        analyzer = CharacterProfileAnalysis(self.ai_api_url, self.timeout)
        generator = GenerateCharacterPrompt(self.ai_api_url, self.timeout)

        chunks = self._chunk_sentences_to_text(sentences, self.CHAR_CHUNK_SIZE)

        all_profiles: dict[str, dict] = {}
        all_alias_map: dict[str, list] = {}

        for i, chunk_text in enumerate(chunks):
            print(
                f"   📖 Character chunk {i+1}/{len(chunks)} ({len(chunk_text)} chars)"
            )
            result = analyzer.run(story_text=chunk_text)

            for profile_data in result.get("character_profile", []):
                name = profile_data["name"]
                if name not in all_profiles:
                    all_profiles[name] = profile_data
                else:
                    existing = all_profiles[name]
                    for field in [
                        "appearance",
                        "outfit",
                        "sex",
                        "age",
                        "race",
                        "base_personality",
                    ]:
                        new_val = profile_data.get(field, "").strip()
                        default_vals = {
                            "not described",
                            "simple casual clothing",
                            "neutral",
                            "human",
                            "adult",
                            "man",
                        }
                        if new_val and new_val not in default_vals:
                            existing[field] = new_val

            for canonical, aliases in result.get("alias_map", {}).items():
                safe_aliases = [a for a in aliases if a != canonical]
                if canonical not in all_alias_map:
                    all_alias_map[canonical] = safe_aliases
                else:
                    all_alias_map[canonical] = list(
                        set(all_alias_map[canonical]) | set(safe_aliases)
                    )

        # ─────────────────────────────────────────────────────────
        # CANONICAL MERGE PASS
        #
        # ปัญหาเดิม:
        #   chunk 1: detect "อาสาม" → all_profiles["อาสาม"] = {...}
        #   chunk 2: detect "เจาอวนหาน" → all_alias_map["เจาอวนหาน"] = ["อาสาม"]
        #   ผลลัพธ์: all_profiles มีทั้ง "อาสาม" และ "เจาอวนหาน" แยกกัน
        #            ทั้งคู่ถูกสร้างเป็น CharacterProfile แยก
        #            ในฉาก LLM เรียก "อาสาม" แต่ profile_map resolve ผิด
        #
        # วิธีแก้:
        #   สร้าง reverse index: alias → canonical_ที่เป็นเจ้าของ
        #   ถ้าชื่อ X ใน all_profiles ปรากฏเป็น alias ของ Y ด้วย
        #   → merge ข้อมูลของ X เข้า Y (ถ้า Y ไม่มีข้อมูลนั้น)
        #   → เพิ่ม X เป็น alias ของ Y
        #   → ลบ X ออกจาก all_profiles
        # ─────────────────────────────────────────────────────────
        all_profiles, all_alias_map = self._merge_alias_conflicts(
            all_profiles, all_alias_map
        )

        self._save_character_profiles(all_profiles, all_alias_map, generator)

    def _merge_alias_conflicts(
        self,
        all_profiles: dict[str, dict],
        all_alias_map: dict[str, list],
    ) -> tuple[dict, dict]:
        """
        ตรวจและแก้กรณีที่ canonical name ของ profile หนึ่ง
        ถูก list เป็น alias ของอีก canonical หนึ่ง

        เช่น:
            all_profiles = {"อาสาม": {...}, "เจาอวนหาน": {...}}
            all_alias_map = {"เจาอวนหาน": ["อาสาม", "อวนหาน"]}

        ผลลัพธ์ที่ถูกต้อง:
            all_profiles = {"เจาอวนหาน": {...}}  ← merge แล้ว, "อาสาม" ถูกดูด
            all_alias_map = {"เจาอวนหาน": ["อาสาม", "อวนหาน"]}
        """
        # สร้าง reverse map: alias_name → canonical_owner
        alias_to_canonical: dict[str, str] = {}
        for canonical, aliases in all_alias_map.items():
            for alias in aliases:
                if alias and alias != canonical:
                    alias_to_canonical[alias] = canonical

        names_to_remove: list[str] = []

        for name in list(all_profiles.keys()):
            if name in alias_to_canonical:
                owner = alias_to_canonical[name]

                # owner อาจยังไม่มี profile (ถ้า detect มาจาก alias map อย่างเดียว)
                if owner not in all_profiles:
                    # ย้าย profile ทั้งก้อนไปให้ owner
                    all_profiles[owner] = dict(all_profiles[name])
                    all_profiles[owner]["name"] = owner
                else:
                    # merge: เติมฟิลด์ที่ owner ยังไม่มีด้วยข้อมูลจาก name
                    orphan_data = all_profiles[name]
                    owner_data = all_profiles[owner]
                    default_vals = {
                        "not described",
                        "simple casual clothing",
                        "neutral",
                        "human",
                        "adult",
                        "man",
                    }
                    for field in [
                        "appearance",
                        "outfit",
                        "sex",
                        "age",
                        "race",
                        "base_personality",
                    ]:
                        orphan_val = orphan_data.get(field, "").strip()
                        owner_val = owner_data.get(field, "").strip()
                        # เติมเฉพาะถ้า owner ยังเป็น default และ orphan มีข้อมูลที่ดีกว่า
                        if (
                            orphan_val
                            and orphan_val not in default_vals
                            and owner_val in default_vals
                        ):
                            owner_data[field] = orphan_val

                # ตรวจว่า name ยังไม่ได้อยู่ใน alias list ของ owner
                existing_aliases = set(all_alias_map.get(owner, []))
                existing_aliases.add(name)
                all_alias_map[owner] = list(existing_aliases - {owner})

                names_to_remove.append(name)
                print(f"   🔀 Merged canonical '{name}' → alias of '{owner}'")

        for name in names_to_remove:
            all_profiles.pop(name, None)
            # ย้าย alias ที่ name เคยเป็นเจ้าของไปให้ owner ด้วย
            # (กรณี "อาสาม" มี alias ย่อยของตัวเอง เช่น "สาม")
            if name in all_alias_map:
                owner = alias_to_canonical[name]
                sub_aliases = all_alias_map.pop(name)
                existing = set(all_alias_map.get(owner, []))
                existing.update(sub_aliases)
                existing.discard(owner)
                all_alias_map[owner] = list(existing)

        # กำจัด alias ที่ยังเป็น canonical name ของคนอื่น (cross-contamination)
        all_canonicals = set(all_profiles.keys())
        for canonical in list(all_alias_map.keys()):
            all_alias_map[canonical] = [
                a
                for a in all_alias_map[canonical]
                if a not in all_canonicals or a == canonical
            ]

        return all_profiles, all_alias_map

    def _chunk_sentences_to_text(self, sentences: list, chunk_size: int) -> list[str]:
        chunks = []
        for i in range(0, len(sentences), chunk_size):
            chunk = sentences[i : i + chunk_size]
            text = "\n".join(s["text"] for s in chunk if s.get("text"))
            if text.strip():
                chunks.append(text)
        return chunks

    def _save_character_profiles(
        self,
        all_profiles: dict,
        all_alias_map: dict,
        generator: GenerateCharacterPrompt,
    ):
        for name, data in all_profiles.items():

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

            aliases = all_alias_map.get(name, [])
            if aliases:
                existing_aliases = set(
                    profile.aliases.split(",") if profile.aliases else []
                )
                new_aliases = existing_aliases | set(aliases)
                new_aliases.discard("")
                profile.aliases = ",".join(sorted(new_aliases))
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

        # สร้าง sorted list ของ sentences ตาม index
        all_sentences_sorted = sorted(sentences, key=lambda x: x["sentence_index"])

        profiles = list(CharacterProfile.objects.filter(novel=self.novel))
        profile_map = self._build_profile_map(profiles)
        all_known_names = list({p.name for p in profiles})

        SceneCharacter.objects.filter(
            session=self.session,
            illustration__chapter=chapter,
        ).delete()

        for illustration in illustrations:
            s_start = illustration.sentence_start or 0
            s_end = illustration.sentence_end or 0

            # ดึงประโยคใน scene พร้อม context เพิ่ม (2 ประโยคก่อนหน้า)
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

            # ส่ง scene_sentences (list of strings) และ scene_description
            char_results = scene_analyzer.analyze(
                sentences=scene_sentences,  # ส่งเป็น list of strings
                character_names=all_known_names,
                scene_description=illustration.scene_description,
            )

            print(
                f"👤 Scene characters with actions: {[(c['name'], c.get('action', '-')) for c in char_results]}"
            )

            scene_char_objs = []
            seen_profiles = set()

            for char_data in char_results:
                name_raw = char_data["name"]
                profile = self._resolve_profile(name_raw, profile_map)

                if not profile:
                    print(f"❌ Cannot resolve character: '{name_raw}'")
                    continue

                if profile.id in seen_profiles:
                    print(f"⚠️  Duplicate profile skipped: '{profile.name}'")
                    continue
                seen_profiles.add(profile.id)

                appearance_anchor = (
                    profile.appearance_tags
                    or profile.appearance
                    or "simple anime character"
                )
                identity = prompt_generator._resolve_identity(profile.sex, profile.age)

                # สร้าง scene context ที่รวม action และ pose
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
        result: dict[str, CharacterProfile] = {}
        for profile in profiles:
            result[self._normalize_name(profile.name)] = profile
            if profile.aliases:
                for alias in profile.aliases.split(","):
                    alias_norm = self._normalize_name(alias)
                    if alias_norm:
                        result[alias_norm] = profile
        return result

    def _resolve_profile(self, name_raw: str, profile_map):
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

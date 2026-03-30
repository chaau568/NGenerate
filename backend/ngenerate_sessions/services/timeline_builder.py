from asset.models import CharacterAsset, NarratorVoice, IllustrationImage
from ngenerate_sessions.models import Sentence, Illustration
from django.conf import settings
import os


class TimelineBuilder:

    def __init__(self, session, generation_run):
        self.session = session
        self.generation_run = generation_run

    # =====================================================
    # PATH HELPER
    # =====================================================

    def _abs(self, path):
        if not path:
            return None
        path = path.replace("\\", "/")

        if path.startswith("/workspace"):
            return path

        full = os.path.join(settings.STORAGE_ROOT, path)
        return full.replace("\\", "/")

    # =====================================================
    # BUILD
    # =====================================================

    def build(self):
        timeline = []

        # =========================
        # LOAD SENTENCES
        # =========================
        sentences = (
            Sentence.objects.filter(session=self.session)
            .select_related("chapter")
            .order_by("chapter__order", "sentence_index")
        )

        # =========================
        # LOAD VOICES
        # =========================
        voices = {
            v.sentence_id: v
            for v in NarratorVoice.objects.filter(generation_run=self.generation_run)
        }

        # =========================
        # LOAD SCENE IMAGES
        # =========================
        scene_images = {
            img.illustration_id: img
            for img in IllustrationImage.objects.filter(
                generation_run=self.generation_run
            ).select_related("illustration")
        }

        # =========================
        # LOAD CHARACTER ASSETS
        # (key = scene_character_id)
        # =========================
        char_assets = {
            a.scene_character_id: a
            for a in CharacterAsset.objects.filter(generation_run=self.generation_run)
        }

        # =========================
        # PRELOAD ILLUSTRATIONS + SCENE CHARACTERS
        # =========================
        illustrations = (
            Illustration.objects.filter(session=self.session)
            .select_related("chapter")
            .prefetch_related("scene_characters")
        )

        # group by chapter
        illustrations_by_chapter = {}
        for ill in illustrations:
            illustrations_by_chapter.setdefault(ill.chapter_id, []).append(ill)

        # =========================
        # HELPER: FIND ILLUSTRATION
        # =========================
        def get_illustration(sentence):
            for ill in illustrations_by_chapter.get(sentence.chapter_id, []):
                if (
                    ill.sentence_start is not None
                    and ill.sentence_end is not None
                    and ill.sentence_start
                    <= sentence.sentence_index
                    <= ill.sentence_end
                ):
                    return ill
            return None

        # =========================
        # OVERLAY CACHE
        # =========================
        last_character_overlays: list[str] = []
        last_illustration_id: int | None = None

        # =========================
        # LOOP
        # =========================
        for sentence in sentences:
            voice = voices.get(sentence.id)
            if not voice:
                continue

            illustration = get_illustration(sentence)
            if not illustration:
                continue

            scene_img = scene_images.get(illustration.id)
            if not scene_img or not scene_img.image:
                continue

            # reset overlay when scene changed
            if illustration.id != last_illustration_id:
                last_character_overlays = []
                last_illustration_id = illustration.id

            # =========================
            # BUILD CHARACTER OVERLAY
            # =========================
            current_overlays = []

            for sc in illustration.scene_characters.all():
                asset = char_assets.get(sc.id)
                if asset and asset.image:
                    current_overlays.append(self._abs(asset.image))

            if current_overlays:
                last_character_overlays = current_overlays

            # =========================
            # APPEND TIMELINE ITEM
            # =========================
            timeline.append(
                {
                    "scene_path": self._abs(scene_img.image),
                    "character_paths": last_character_overlays,
                    "audio_path": self._abs(voice.voice),
                    "duration": voice.duration,
                    "subtitle": sentence.sentence,
                }
            )

        return timeline

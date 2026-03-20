from asset.models import CharacterAsset, NarratorVoice, IllustrationImage
from ngenerate_sessions.models import Sentence
from django.conf import settings
import os


class TimelineBuilder:

    def __init__(self, session, generation_run):
        self.session = session
        self.generation_run = generation_run

    def _abs(self, path):
        if not path:
            return None
        path = path.replace("\\", "/")
        if path.startswith("/workspace"):
            return path
        full = os.path.join(settings.STORAGE_ROOT, path)
        return full.replace("\\", "/")

    def build(self):
        timeline = []

        sentences = (
            Sentence.objects.filter(session=self.session)
            .select_related("chapter")
            .prefetch_related(
                "sentence_characters__character__illustration",
                "sentence_characters__character__character_profile",
            )
            .order_by("chapter__order", "sentence_index")
        )

        voices = {
            v.sentence_id: v
            for v in NarratorVoice.objects.filter(generation_run=self.generation_run)
        }

        scene_images = {
            img.illustration_id: img
            for img in IllustrationImage.objects.select_related("illustration").filter(
                generation_run=self.generation_run  # ←
            )
        }

        char_assets = {
            a.character_id: a
            for a in CharacterAsset.objects.filter(
                generation_run=self.generation_run
            )  # ←
        }

        last_character_overlays: list[str] = []
        last_illustration_id: int | None = None

        for sentence in sentences:
            voice = voices.get(sentence.id)
            if not voice:
                continue

            illustration = None
            for sc in sentence.sentence_characters.all():
                if sc.character.illustration:
                    illustration = sc.character.illustration
                    break

            if not illustration:
                from ngenerate_sessions.models import Illustration

                illustration = Illustration.objects.filter(
                    session=self.session,
                    chapter=sentence.chapter,
                    sentence_start__lte=sentence.sentence_index,
                    sentence_end__gte=sentence.sentence_index,
                ).first()

            if not illustration:
                continue

            scene_img = scene_images.get(illustration.id)
            if not scene_img:
                continue

            if illustration.id != last_illustration_id:
                last_character_overlays = []
                last_illustration_id = illustration.id

            current_overlays = []
            for sc in sentence.sentence_characters.all():
                asset = char_assets.get(sc.character_id)
                if asset and asset.image:
                    current_overlays.append(self._abs(asset.image))

            if current_overlays:
                last_character_overlays = current_overlays

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

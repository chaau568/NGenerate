from asset.models import CharacterAsset, NarratorVoice, IllustrationImage
from ngenerate_sessions.models import Sentence
from django.conf import settings
import os


class TimelineBuilder:

    def __init__(self, session):
        self.session = session

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
            .prefetch_related("sentence_characters__character")
            .order_by("chapter__order", "sentence_index")
        )

        voices = {
            v.sentence_id: v for v in NarratorVoice.objects.filter(session=self.session)
        }

        scenes = {
            img.illustration.chapter_id: img
            for img in IllustrationImage.objects.select_related("illustration").filter(
                session=self.session
            )
        }

        char_assets = {
            a.character_id: a
            for a in CharacterAsset.objects.filter(session=self.session)
        }

        for sentence in sentences:

            voice = voices.get(sentence.id)

            if not voice:
                continue

            scene = scenes.get(sentence.chapter_id)

            if not scene:
                continue

            character_overlays = []

            for sc in sentence.sentence_characters.all():

                asset = char_assets.get(sc.character_id)

                if asset and asset.image:
                    character_overlays.append(self._abs(asset.image))

            timeline.append(
                {
                    "scene_path": self._abs(scene.image),
                    "character_paths": character_overlays,
                    "audio_path": self._abs(voice.voice),
                    "duration": voice.duration,
                    "subtitle": sentence.sentence,
                }
            )

        return timeline

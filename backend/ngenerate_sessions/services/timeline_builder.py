from asset.models import CharacterAsset, NarratorVoice, IllustrationImage
from ngenerate_sessions.models import Sentence


class TimelineBuilder:
    def __init__(self, session):
        self.session = session

    def build(self):
        timeline = []
        sentences = (
            Sentence.objects.filter(session=self.session)
            .select_related("chapter")
            .prefetch_related("sentence_characters__character_profile")
            .order_by("chapter__order", "sentence_index")
        )

        for sentence in sentences:
            # 1. ดึงเสียงพากย์
            voice = NarratorVoice.objects.filter(
                session=self.session,
                sentence=sentence,
            ).first()

            if not voice:
                continue

            # 2. ดึงฉากหลัง (Scene) ของ Chapter นี้
            scene = IllustrationImage.objects.filter(
                session=self.session,
                illustration__chapter=sentence.chapter,
            ).first()

            # 3. ดึงภาพตัวละครที่อยู่ในประโยคนี้ (ตาม Emotion ของประโยค)
            character_overlays = []
            for sc in sentence.sentence_characters.all():
                char_image = CharacterAsset.objects.filter(
                    session=self.session,
                    character__chapter=sentence.chapter,
                    character__character_profile=sc.character_profile,
                    character__emotion=sentence.emotion,
                ).first()

                if char_image:
                    character_overlays.append(char_image.image.path)

            timeline.append(
                {
                    "scene_path": scene.image.path if scene else None,
                    "character_paths": character_overlays,  
                    "audio_path": voice.voice.path,
                    "duration": voice.duration,
                    "subtitle": sentence.sentence,
                }
            )

        return timeline

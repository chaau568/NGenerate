from ngenerate_sessions.models import Sentence, Illustration
from asset.models import CharacterImage, CharacterVoice, IllustrationImage


class TimelineBuilder:

    def __init__(self, session):
        self.session = session

    def build(self):

        timeline = []
        current_time = 0.0

        chapters = (
            self.session.chapters
            .all()
            .order_by("id")
        )

        for chapter in chapters:

            # 1 scene per chapter
            illustration = Illustration.objects.get(
                session=self.session,
                chapter=chapter
            )

            scene_image = IllustrationImage.objects.get(
                session=self.session,
                illustration=illustration
            )

            sentences = (
                Sentence.objects
                .filter(session=self.session, chapter=chapter)
                .order_by("sentence_index")
            )

            active_character_image = None

            for sentence in sentences:

                voice = CharacterVoice.objects.filter(
                    session=self.session,
                    sentence=sentence
                ).first()

                duration = voice.duration if voice else 2.0

                character_image = None

                if sentence.type == "dialogue" and sentence.character:

                    char_img = CharacterImage.objects.get(
                        session=self.session,
                        character=sentence.character
                    )

                    character_image = char_img.image.url
                    active_character_image = character_image

                elif sentence.type == "narration":
                    character_image = None

                else:
                    character_image = active_character_image

                timeline.append({
                    "start": current_time,
                    "end": current_time + duration,
                    "background": scene_image.image.url,
                    "character_overlay": character_image,
                    "audio": voice.voice.url if voice else None,
                })

                current_time += duration

        return timeline
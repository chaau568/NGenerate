from asset.models import CharacterVoice

def create_voice(sentence, voice_file, duration):
    """
    sentence: SentenceAnalysis
    voice_file: audio file
    duration: float (seconds)
    """

    voice_obj, created = CharacterVoice.objects.update_or_create(
        sentence=sentence,
        defaults={
            "voice": voice_file,
            "duration": duration
        }
    )

    return voice_obj

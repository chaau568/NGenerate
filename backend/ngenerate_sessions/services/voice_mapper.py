class VoiceMapper:

    VALID_EMOTIONS = {"neutral", "happy", "sad", "angry", "serious"}

    DEFAULT_VOICE = "man1"

    @staticmethod
    def map_from_profile(profile, sentence):

        voice_type = getattr(profile, "voice_type", None)

        if not voice_type:
            voice_type = VoiceMapper.DEFAULT_VOICE

        emotion = (sentence.emotion or "neutral").lower()

        if emotion not in VoiceMapper.VALID_EMOTIONS:
            emotion = "neutral"

        return voice_type, emotion
class VoiceMapper:

    VALID_EMOTIONS = {"neutral", "happy", "sad", "angry", "serious"}
    DEFAULT_VOICE = "man1"

    # EMOTION_CONFIGS = {
    #     "happy": {"speed": 1.0, "cross_fade_duration": 0.1, "step": 50, "cfg": 3.0},
    #     "neutral": {"speed": 1.0, "cross_fade_duration": 0.1, "step": 48, "cfg": 2.5},
    #     "angry": {"speed": 1.1, "cross_fade_duration": 0.3, "step": 48, "cfg": 3.0},
    #     "sad": {"speed": 0.9, "cross_fade_duration": 0.1, "step": 48, "cfg": 2.0},
    #     "serious": {"speed": 1.0, "cross_fade_duration": 0.1, "step": 50, "cfg": 2.5},
    # }
    
    EMOTION_CONFIGS = {
        "happy": {"speed": 0.8, "cross_fade_duration": 0.1, "step": 64, "cfg": 2.5},
        "neutral": {"speed": 0.8, "cross_fade_duration": 0.1, "step": 64, "cfg": 2.5},
        "angry": {"speed": 0.8, "cross_fade_duration": 0.1, "step": 64, "cfg": 2.5},
        "sad": {"speed": 0.8, "cross_fade_duration": 0.1, "step": 64, "cfg": 2.5},
        "serious": {"speed": 0.8, "cross_fade_duration": 0.1, "step": 64, "cfg": 2.5},
    }

    @staticmethod
    def map(session, sentence):

        voice_type = session.narrator_voice or VoiceMapper.DEFAULT_VOICE

        emotion = (sentence.emotion or "neutral").lower()

        if emotion not in VoiceMapper.VALID_EMOTIONS:
            emotion = "neutral"

        config = VoiceMapper.EMOTION_CONFIGS.get(
            emotion, VoiceMapper.EMOTION_CONFIGS["neutral"]
        )

        return voice_type, emotion, config

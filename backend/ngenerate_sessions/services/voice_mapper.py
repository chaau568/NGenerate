class VoiceMapper:

    @staticmethod
    def generate_voice_key(sex, age, emotion, tone="tone1"):
        """
        Create master voice id
        Example: male_adult_happy_tone2
        """

        return f"{sex}_{age}_{emotion}_{tone}"

    @staticmethod
    def map_from_profile(profile, sentence):
        """
        profile -> Character profile
        sentence -> Sentence model
        """

        sex = profile.sex
        age = profile.age
        emotion = sentence.emotion or "neutral"

        # optional random tone
        tone = "tone1"

        return VoiceMapper.generate_voice_key(sex, age, emotion, tone)
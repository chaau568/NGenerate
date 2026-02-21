from django.conf import settings

class CreditPricing:
    CHAPTER_UNIT = settings.CREDIT_CHAPTER_PER_UNIT
    SENTENCE_UNIT = settings.CREDIT_SENTENCE_PER_UNIT
    CHARACTER_IMAGE = settings.CREDIT_CHARACTER_IMAGE
    SCENE_IMAGE = settings.CREDIT_SCENE_IMAGE

    @classmethod
    def sentence_to_credit(cls, sentence_count):
        return sentence_count // cls.SENTENCE_UNIT

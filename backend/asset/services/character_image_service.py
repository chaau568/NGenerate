from asset.models import CharacterImage

def create_character_image(character_profile, emotion, image_file):
    """
    character_profile: CharacterProfileAnalysis
    emotion: str เช่น happy / angry
    image_file: File จาก AI หรือ storage
    """

    image_obj, created = CharacterImage.objects.update_or_create(
        character_profile=character_profile,
        emotion=emotion,
        defaults={
            "image": image_file
        }
    )

    return image_obj

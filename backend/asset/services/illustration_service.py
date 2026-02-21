from asset.models import IllustrationImage

def create_illustration_image(illustration, image_file):
    return IllustrationImage.objects.update_or_create(
        illustration=illustration,
        defaults={
            "image": image_file
        }
    )[0]

from django.conf import settings


def build_file_url(path):
    if not path:
        return None

    clean_path = path.lstrip("/")

    return f"{settings.BASE_FILE_URL}/{clean_path}"
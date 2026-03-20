# from django.conf import settings


# def build_file_url(path):
#     if not path:
#         return None

#     clean_path = path.lstrip("/")

#     return f"{settings.BASE_FILE_URL}/{clean_path}"

# utils/file_url.py
from django.conf import settings


def build_file_url(path: str | None) -> str | None:
    if not path:
        return None

    path = path.replace("\\", "/")

    # full URL อยู่แล้ว → คืนตรงๆ
    if path.startswith("http://") or path.startswith("https://"):
        return path

    # ตัด STORAGE_ROOT ออกถ้ามี
    # เช่น /workspace/ngenerate/user_data/... → user_data/...
    storage_root = settings.STORAGE_ROOT.replace("\\", "/").rstrip("/")
    if path.startswith(storage_root):
        path = path[len(storage_root) :].lstrip("/")

    # ตัด leading slash ที่เหลือ
    path = path.lstrip("/")

    base = settings.BASE_FILE_URL.rstrip("/")
    return f"{base}/{path}"

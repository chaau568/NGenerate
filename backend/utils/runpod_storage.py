import requests
from django.conf import settings

AI_FILES_API = f"{settings.AI_API_URL}/files"


def list_runpod_files(path=""):
    """รายการไฟล์และโฟลเดอร์"""
    url = f"{AI_FILES_API}/list"
    try:
        r = requests.get(url, params={"path": path}, timeout=10)
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        print(f"RunPod list_files error: {e}")
        return None


def get_runpod_preview_url(path):
    return f"{AI_FILES_API}/preview?path={path}"


def get_runpod_download_url(path):
    """ส่งคืน URL สำหรับดาวน์โหลด"""
    return f"{AI_FILES_API}/download?path={path}"


def delete_runpod_file(path):
    url = AI_FILES_API
    try:
        r = requests.delete(url, params={"path": path}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"RunPod delete_file error: {e}")
        return False


def delete_runpod_folder(path):
    url = f"{AI_FILES_API}/folder"
    try:
        r = requests.delete(url, params={"path": path}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"RunPod delete_folder error: {e}")
        return False

from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from utils.file_url import build_file_url

from .models import (
    CharacterProfileAsset,
    CharacterAsset,
    NarratorVoice,
    IllustrationImage,
    Video,
)
from ngenerate_sessions.models import Session


@extend_schema(
    summary="ดึง Assets ทั้งหมดของ Session",
    description="ดึงข้อมูลภาพต้นแบบ, ภาพอารมณ์ตัวละคร, เสียง, ภาพฉาก และวิดีโอ",
    parameters=[OpenApiParameter(name="session_id", required=True, type=int)],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_assets(request):
    session_id = request.query_params.get("session_id")
    if not session_id:
        return Response(
            {"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    session = get_object_or_404(Session, id=session_id, novel__user=request.user)

    char_images = CharacterProfileAsset.objects.filter(
        character_profile__novel=session.novel
    ).select_related("character_profile")

    emotion_images = CharacterAsset.objects.filter(session=session).select_related(
        "character__character_profile", "character__chapter"
    )

    char_voices = NarratorVoice.objects.filter(session=session).select_related(
        "sentence"
    )
    illustrations = IllustrationImage.objects.filter(session=session).select_related(
        "illustration__chapter"
    )
    videos = Video.objects.filter(session=session).order_by("-version")

    data = {
        "session_id": session.id,
        "character_master_images": [
            {
                "id": img.id,
                "character_id": img.character_profile.id,
                "character_name": img.character_profile.name,
                "url": build_file_url(img.image) if img.image else None,
            }
            for img in char_images
        ],
        "character_emotion_images": [
            {
                "id": img.id,
                "character_name": img.character.character_profile.name,
                "emotion": img.character.emotion,
                "chapter_order": img.character.chapter.order,
                "url": build_file_url(img.image) if img.image else None,
            }
            for img in emotion_images
        ],
        "character_voices": [
            {
                "id": v.id,
                "sentence_index": v.sentence.sentence_index,
                "url": build_file_url(v.voice) if v.voice else None,
                "duration": v.duration,
            }
            for v in char_voices
        ],
        "illustrations": [
            {
                "id": ill.id,
                "chapter_order": ill.illustration.chapter.order,
                "url": build_file_url(ill.image) if ill.image else None,
            }
            for ill in illustrations
        ],
        "videos": [
            {
                "id": vid.id,
                "version": vid.version,
                "url": build_file_url(vid.video_path) if vid.video_path else None,
                "duration": str(vid.duration) if vid.duration else None,
                "is_final": vid.is_final,
                "created_at": vid.created_at,
            }
            for vid in videos
        ],
    }

    return Response(data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_video(request, video_id):
    video = get_object_or_404(Video, id=video_id, session__novel__user=request.user)
    video.delete()
    return Response(
        {"message": "Video deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def watch_video(request, video_id):

    video = get_object_or_404(Video, id=video_id, session__novel__user=request.user)

    if not video.video_path:
        return Response({"error": "Video not found"}, status=404)

    video_url = build_file_url(video.video_path)

    return redirect(video_url)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_video(request, video_id):

    video = get_object_or_404(Video, id=video_id, session__novel__user=request.user)

    return Response(
        {"download_url": build_file_url(video.video_path) if video.video_path else None}
    )

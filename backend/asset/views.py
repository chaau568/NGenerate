from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiParameter

from django.http import FileResponse, Http404
from django.utils.encoding import smart_str
import os

from .models import CharacterImage, CharacterVoice, IllustrationImage, Video
from ngenerate_sessions.models import Session


@extend_schema(
    summary="ดึง Assets ทั้งหมดของ Session",
    description="ดึงข้อมูลภาพตัวละคร, เสียง, ภาพประกอบ และวิดีโอ ที่เกี่ยวข้องกับ Session ID ที่ระบุ",
    parameters=[
        OpenApiParameter(
            name="session_id",
            description="ID ของ Session ที่ต้องการดึงข้อมูล",
            required=True,
            type=int,
        )
    ],
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def session_assets(request):
    session_id = request.query_params.get("session_id")
    if not session_id:
        return Response(
            {"error": "session_id is required"}, status=status.HTTP_400_BAD_REQUEST
        )

    session = get_object_or_404(Session, id=session_id, user=request.user)

    char_images = CharacterImage.objects.filter(session=session)
    char_voices = CharacterVoice.objects.filter(session=session)
    illustrations = IllustrationImage.objects.filter(session=session)
    videos = Video.objects.filter(session=session).order_by("-version")

    data = {
        "session_id": session.id,
        "character_images": [
            {
                "id": img.id,
                "character_id": img.character.id,
                "character_name": img.character.name,
                "url": request.build_absolute_uri(img.image.url),
                "created_at": img.created_at,
            }
            for img in char_images
        ],
        "character_voices": [
            {
                "id": v.id,
                "sentence_id": v.sentence.id,
                "url": request.build_absolute_uri(v.voice.url),
                "duration": v.duration,
                "created_at": v.created_at,
            }
            for v in char_voices
        ],
        "illustrations": [
            {
                "id": ill.id,
                "illustration_id": ill.illustration.id,
                "url": request.build_absolute_uri(ill.image.url),
                "created_at": ill.created_at,
            }
            for ill in illustrations
        ],
        "videos": [
            {
                "id": vid.id,
                "name": vid.name,
                "version": vid.version,
                "url": request.build_absolute_uri(vid.video_file.url),
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
    video = get_object_or_404(Video, id=video_id, session__user=request.user)
    video.delete()
    return Response(
        {"message": "Video deleted successfully"}, status=status.HTTP_204_NO_CONTENT
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def watch_video(request, video_id):
    video = get_object_or_404(Video, id=video_id, session__user=request.user)

    if not video.video_file:
        raise Http404("Video file not found")

    file_path = video.video_file.path

    response = FileResponse(open(file_path, "rb"), content_type="video/mp4")

    response["Content-Disposition"] = (
        f'inline; filename="{smart_str(os.path.basename(file_path))}"'
    )
    response["Content-Length"] = os.path.getsize(file_path)

    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_video(request, video_id):
    video = get_object_or_404(Video, id=video_id, session__novel__user=request.user)

    if not video.video_file:
        raise Http404("Video file not found")

    file_path = video.video_file.path

    response = FileResponse(open(file_path, "rb"), content_type="video/mp4")

    response["Content-Disposition"] = (
        f'attachment; filename="{smart_str(os.path.basename(file_path))}"'
    )

    return response

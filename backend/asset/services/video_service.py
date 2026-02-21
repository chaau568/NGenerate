from asset.models import Video

def create_video(session, name, video_file, duration, file_size):
    last_version = (
        Video.objects
        .filter(analysis_session=session)
        .aggregate(models.Max("version"))["version__max"]
        or 0
    )

    video = Video.objects.create(
        analysis_session=session,
        name=name,
        version=last_version + 1,
        video_file=video_file,
        duration=duration,
        file_size=file_size,
        status="completed"
    )

    return video

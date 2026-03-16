from pathlib import Path

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    ColorClip,
    TextClip,
    concatenate_videoclips,
)


class VideoComposer:

    def __init__(self, timeline, output_dir):

        self.timeline = timeline
        self.output_dir = Path(output_dir)

        self.width = 1280
        self.height = 720

    def compose(self):

        clips = []

        for item in self.timeline:

            clip = self._build_scene_clip(item)

            if clip:
                clips.append(clip)

        if not clips:
            return None, 0

        final_video = concatenate_videoclips(clips, method="compose")

        self.output_dir.mkdir(parents=True, exist_ok=True)

        output_path = self.output_dir / "final_video.mp4"

        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
        )

        return str(output_path), final_video.duration

    # ------------------------------------------------

    def _build_scene_clip(self, item):

        duration = item["duration"]

        if not duration:
            duration = 3

        layers = []

        # -------------------------
        # Scene
        # -------------------------

        if item["scene_path"]:

            bg_clip = (
                ImageClip(item["scene_path"])
                .set_duration(duration)
                .resize(height=self.height)
            )

        else:

            bg_clip = ColorClip(
                size=(self.width, self.height),
                color=(0, 0, 0),
                duration=duration,
            )

        layers.append(bg_clip)

        # -------------------------
        # Characters
        # -------------------------

        for char_path in item["character_paths"]:

            char_clip = (
                ImageClip(char_path)
                .set_duration(duration)
                .resize(height=self.height * 0.8)
                .set_position(("center", "bottom"))
            )

            layers.append(char_clip)

        # -------------------------
        # Audio
        # -------------------------

        audio_clip = AudioFileClip(item["audio_path"])

        # -------------------------
        # Subtitle
        # -------------------------

        if item.get("subtitle"):

            subtitle_clip = self._create_subtitle(item["subtitle"], duration)

            layers.append(subtitle_clip)

        # -------------------------

        final_clip = CompositeVideoClip(layers, size=(self.width, self.height))

        final_clip = final_clip.set_audio(audio_clip)

        return final_clip

    # ------------------------------------------------

    def _create_subtitle(self, text, duration):

        subtitle = TextClip(
            text,
            fontsize=40,
            font="DejaVu-Sans",
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="caption",
            size=(self.width * 0.8, None),
        )

        subtitle = subtitle.set_position(("center", self.height * 0.85))

        subtitle = subtitle.set_duration(duration)

        return subtitle

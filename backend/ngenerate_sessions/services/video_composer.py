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
            return None

        final_video = concatenate_videoclips(clips, method="compose")
        output_path = (
            self.output_dir
            / f"session_{self.timeline[0].get('session_id', 'final')}.mp4"
        )

        # สร้าง folder ถ้ายังไม่มี
        self.output_dir.mkdir(parents=True, exist_ok=True)

        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio_codec="aac",
        )
        return str(output_path)

    def _build_scene_clip(self, item):
        duration = item["duration"]
        layers = []

        # 1. Background Layer (ฉากหลัง)
        if item["scene_path"]:
            bg_clip = ImageClip(item["scene_path"]).set_duration(duration)
            bg_clip = bg_clip.resize(height=self.height)  # ปรับให้เต็มจอ
            layers.append(bg_clip)
        else:
            # กรณีไม่มีฉากหลัง ให้ใช้สีดำแทน
            bg_clip = ColorClip(
                size=(self.width, self.height), color=(0, 0, 0)
            ).set_duration(duration)
            layers.append(bg_clip)

        # 2. Character Overlays (ตัวละครซ้อนทับ)
        for char_path in item["character_paths"]:
            char_clip = ImageClip(char_path).set_duration(duration)
            # ปรับขนาดตัวละคร (เช่น ให้สูง 80% ของจอ) และวางไว้กึ่งกลางล่าง
            char_clip = char_clip.resize(height=self.height * 0.8)
            char_clip = char_clip.set_position(("center", "bottom"))
            layers.append(char_clip)

        # 3. Audio Layer
        audio_clip = AudioFileClip(item["audio_path"])

        # 4. Subtitle Layer
        if item.get("subtitle"):
            subtitle_clip = self._create_subtitle(item["subtitle"], duration)
            layers.append(subtitle_clip)

        # รวมทุก Layer
        final_clip = CompositeVideoClip(layers, size=(self.width, self.height))
        final_clip = final_clip.set_audio(audio_clip)

        return final_clip

    def _create_subtitle(self, text, duration):
        subtitle = TextClip(
            text,
            fontsize=36,
            font="Arial-Bold",  
            color="white",
            stroke_color="black",
            stroke_width=1.5,
            method="caption",
            size=(self.width * 0.8, None),
        )

        subtitle = subtitle.set_position(("center", self.height * 0.85))
        subtitle = subtitle.set_duration(duration)
        return subtitle

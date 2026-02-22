import os
import subprocess
import uuid


class VideoComposer:

    def __init__(self, timeline, output_dir):
        self.timeline = timeline
        self.output_dir = output_dir

    def compose(self):

        segment_files = []

        for index, segment in enumerate(self.timeline):

            segment_path = self._render_segment(segment, index)
            segment_files.append(segment_path)

        final_video = self._concat_segments(segment_files)

        return final_video

    # =========================================
    # RENDER SINGLE SEGMENT
    # =========================================

    def _render_segment(self, segment, index):

        output_path = os.path.join(
            self.output_dir,
            f"segment_{index}.mp4"
        )

        background = segment["background"]
        overlay = segment["character_overlay"]
        audio = segment["audio"]
        duration = segment["end"] - segment["start"]

        cmd = [
            "ffmpeg",
            "-y",
            "-loop", "1",
            "-i", background,
        ]

        if overlay:
            cmd += ["-i", overlay]

        if audio:
            cmd += ["-i", audio]

        filter_complex = []

        if overlay:
            filter_complex.append(
                "overlay=(main_w-overlay_w-50):(main_h-overlay_h-50)"
            )

        cmd += [
            "-filter_complex", ",".join(filter_complex) if filter_complex else "null",
            "-t", str(duration),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-shortest",
            output_path
        ]

        subprocess.run(cmd, check=True)

        return output_path

    # =========================================
    # CONCAT
    # =========================================

    def _concat_segments(self, segments):

        list_file = os.path.join(self.output_dir, "list.txt")

        with open(list_file, "w") as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        final_path = os.path.join(
            self.output_dir,
            f"final_{uuid.uuid4().hex}.mp4"
        )

        cmd = [
            "ffmpeg",
            "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_file,
            "-c", "copy",
            final_path
        ]

        subprocess.run(cmd, check=True)

        return final_path
# video_generator.py - OPTIMIZED VERSION
from proglog import ProgressBarLogger
import re
import os

from moviepy.config import change_settings
from moviepy.editor import (
    ImageClip,
    ColorClip,
    TextClip,
    CompositeVideoClip,
)

# ================= IMAGEMAGICK =================
if os.name == "nt":  # Windows
    change_settings({
        "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
    })
else:
    # CHANGE 5: On Linux/AWS, try "magick" first (ImageMagick 7) and fall back
    # to "convert" (ImageMagick 6, which ships on older Ubuntu AMIs via apt).
    # Without this fallback the app crashes silently at TextClip on some EC2 AMIs.
    import shutil
    _magick = "magick" if shutil.which("magick") else "convert"
    change_settings({"IMAGEMAGICK_BINARY": _magick})

# ================= CONFIG =================
# CHANGE 6: Build font_path relative to this file's directory instead of
# using a bare relative path. A bare "fonts/..." path breaks when Gunicorn
# is started from a directory other than the project root on AWS.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    "resolution": (854, 480),  # 480p
    "fps": 20,
    "font_path": os.path.join(_BASE_DIR, "fonts", "NotoSansTelugu-Bold.ttf")
}


def generate_video(
    text,
    background_path,
    scroll_speed=50,
    font_size=40,
    main_color="black",
    progress_func=None,
    output_path="output/final_video.mp4",
):

    def update(val):
        if progress_func:
            progress_func(val)

    # ================= TEXT CLEAN =================
    print("Creating text clip...")

    text = re.sub(r'\s+', ' ', text).strip()

    side_margin = 5
    text_width = CONFIG["resolution"][0] - (side_margin * 2)

    # CHANGE 7: Verify the font file actually exists before passing it to
    # ImageMagick. On AWS a missing font causes a cryptic ImageMagick error;
    # this gives a clear message and stops early instead.
    if not os.path.exists(CONFIG["font_path"]):
        raise FileNotFoundError(
            f"Font not found: {CONFIG['font_path']}. "
            "Make sure the fonts/ folder is uploaded alongside the app."
        )

    # ================= TEXT CLIP =================
    text_clip = TextClip(
        text,
        font=CONFIG["font_path"],
        fontsize=font_size,
        color=main_color,
        size=(text_width, None),
        method="caption",
        align="center",
        interline=-5
    )

    text_height = text_clip.h
    duration = (text_height + CONFIG["resolution"][1]) / scroll_speed

    text_clip = text_clip.set_duration(duration)

    # Scroll bottom to top
    text_clip = text_clip.set_position(
        lambda t: (
            "center",
            CONFIG["resolution"][1] - scroll_speed * t
        )
    )

    print(f"Text clip ready: {duration:.1f}s")

    # ================= BACKGROUND =================
    try:
        background = ImageClip(background_path)

        if background.size != CONFIG["resolution"]:
            background = background.resize(CONFIG["resolution"])

        background = background.set_duration(duration)

        print("Background loaded")

    except Exception:
        print("Background failed, using black background")
        background = ColorClip(CONFIG["resolution"], color=(0, 0, 0)).set_duration(duration)

    # ================= COMPOSITE =================
    print("Compositing video...")

    final_video = CompositeVideoClip(
        [background, text_clip],
        size=CONFIG["resolution"]
    )

    # ================= PROGRESS LOGGER =================
    class MyBarLogger(ProgressBarLogger):
        def bars_callback(self, bar, attr, value, old_value=None):

            if progress_func and bar == 't':

                total = self.bars[bar]['total']

                if total:
                    percent = int((value / total) * 100)
                    progress_func(percent)

    logger = MyBarLogger()

    # ================= EXPORT =================
    print("Exporting video...")

    # CHANGE 8: Reduced threads from 4 to 2. On a t3.medium (2 vCPU) using 4
    # ffmpeg threads causes context switching overhead and can make the instance
    # unresponsive. 2 threads matches the vCPU count and is the safe default.
    final_video.write_videofile(
        output_path,
        fps=CONFIG["fps"],
        codec="libx264",
        audio=False,
        threads=2, # for 2 vCPU machines; adjust if you know your server has more cores
        preset="ultrafast",
        ffmpeg_params=[
            "-crf", "26",
            "-movflags", "+faststart",
        ],
        logger=logger,
    )

    print("=" * 50)
    print("VIDEO COMPLETE!")
    print(f"File: {output_path}")
    print(f"Duration: {duration:.1f}s")
    print("=" * 50)

    if progress_func:
        progress_func(100)

    return os.path.basename(output_path)
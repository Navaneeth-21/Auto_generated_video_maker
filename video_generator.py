from proglog import ProgressBarLogger

import re
from moviepy.config import change_settings

change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
})

import os
import numpy as np
from moviepy.editor import (
    ImageClip,
    ColorClip,
    TextClip,
    VideoFileClip,
    CompositeVideoClip,
    concatenate_videoclips,
)

from moviepy.video.fx.all import fadein, fadeout

# ================= CONFIG =================
CONFIG = {
    "resolution": (854, 480),  # can change to (1280, 720) if desired
    "fps": 15,
    "font_size": 40,
    "pip_size": (260, 260),
    "pip_opacity": 1.0,
    "font_path": r"D:\video_maker\fonts\NotoSansTelugu-Regular.ttf"
    # change to your desired font or full path
}


def generate_video(
    text,
    background_path,
    pip_path,
    intro_path,
    scroll_speed=50,
    font_size=40,
    main_color="black",
    shadow_color="white",
    progress_func=None,
    output_path="output/final_video.mp4",):

    def update(val):
        if progress_func:
            progress_func(val)


   
# ================= TEXT CLIP (PIL DIRECT RENDER - BEST METHOD) =================
    print("🖋️ Creating text clip with PIL rendering...")
    # Convert pasted line breaks into normal paragraph
    text = re.sub(r'\s+', ' ', text).strip()

    side_margin = 5   # small margin on each side
    text_width = CONFIG["resolution"][0] - (side_margin * 2)

    shadow_clip = TextClip(
    text,
    font="fonts/NotoSansTelugu-Regular.ttf",
    fontsize=font_size,
    color=shadow_color,
    size=(text_width, None),
    method="caption",
    align="center",
    )

    main_clip = TextClip(
    text,
    font="fonts/NotoSansTelugu-Regular.ttf",
    fontsize=font_size,
    color=main_color,
    size=(text_width, None),
    method="caption",
    align="center",
    )

    shadow_offsets = [
    (-2, -2), (2, -2),
    (-2, 2),  (2, 2),
    (-3, 0),  (3, 0),
    (0, -3),  (0, 3)
    ]

    shadow_clips = [
        shadow_clip.set_position((side_margin + dx, dy))
        for dx, dy in shadow_offsets
    ]

    main_clip = main_clip.set_position((side_margin, 0))

    text_clip = CompositeVideoClip(shadow_clips + [main_clip])

    text_height = text_clip.h
    duration = (text_height + CONFIG["resolution"][1]) / scroll_speed
    text_clip = text_clip.set_duration(duration)

    def scroll_position(t):
        y = CONFIG["resolution"][1] - int(scroll_speed * t)
        x = side_margin  # keep text centered with margin
        return (x, y)

    text_clip = text_clip.set_position(scroll_position)

    # ================= BACKGROUND =================
    
    try:
        background = (
            ImageClip(background_path)
            .resize(CONFIG["resolution"])
            .set_duration(duration)
        )
        print("✅ Background loaded & resized")

    except Exception as e:
        print(f"⚠ Background failed: {str(e)} → using black background")
        background = ColorClip(CONFIG["resolution"], color=(0, 0, 0)).set_duration(duration)

    # ================= PIP VIDEO =================

    has_pip = False
    pip_audio = None

    try:
        pip = VideoFileClip(pip_path)

        if pip.duration < duration:
            loops = int(duration / pip.duration) + 1
            pip = concatenate_videoclips([pip] * loops)
            print(f"🔄 PIP looped {loops} times")

        pip = pip.subclip(0, duration).resize(CONFIG["pip_size"])

        # ---------- MAKE CIRCULAR MASK ----------
        w, h = CONFIG["pip_size"]
        radius = min(w, h) // 2

        y, x = np.ogrid[:h, :w]
        center_x, center_y = w // 2, h // 2
        distance = (x - center_x) ** 2 + (y - center_y) ** 2

        # IMPORTANT: float mask between 0 and 1
        mask = np.zeros((h, w), dtype=float)
        mask[distance <= radius ** 2] = 1.0

        mask_clip = ImageClip(mask, ismask=True).set_duration(duration)

        pip = pip.set_mask(mask_clip)
        # -----------------------------------------

        pip_x = (CONFIG["resolution"][0] - CONFIG["pip_size"][0]) // 2
        pip_y = (CONFIG["resolution"][1] - CONFIG["pip_size"][1]) // 2

        pip = pip.set_position((pip_x, pip_y)).set_opacity(CONFIG["pip_opacity"])

        pip_audio = pip.audio
        has_pip = True
        

    except Exception as e:
        print(f"⚠ PIP failed: {str(e)} → skipping")


    # ================= COMPOSITE MAIN =================
    print("🎨 Compositing layers...")

    layers = [background, text_clip]
    if has_pip:
        layers.insert(1, pip)  # PIP between background and text

    main_video = CompositeVideoClip(layers, size=CONFIG["resolution"])

    if has_pip and pip_audio:
        main_video = main_video.set_audio(pip_audio)
        print("🔊 Audio from PIP added")

    # ================= INTRO + TRANSITION =================
    print("🎬 Adding intro with fade transition...")

    transition = 1.0
    final_video = main_video
    try:
        intro = VideoFileClip(intro_path).resize(CONFIG["resolution"])
        print(f"✅ Intro loaded ({intro.duration:.1f}s)")

        intro = fadeout(intro, transition)
        main_video = fadein(main_video, transition)


        final_video = concatenate_videoclips(
            [intro, main_video],
            method="compose",
            padding=-transition,
        )
        print("✅ Intro + smooth fade added")

    except Exception as e:
        print(f"⚠ Intro failed: {str(e)} → skipping intro")

    # ================= EXPORT =================
    class MyBarLogger(ProgressBarLogger):
        def bars_callback(self, bar, attr, value, old_value=None):
            if progress_func and bar == 't':
                total = self.bars[bar]['total']
                if total:
                    percent = int((value / total) * 100)
                    progress_func(percent)


    logger = MyBarLogger()

    final_video.write_videofile(
        output_path,
        fps=CONFIG["fps"],
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=4,
        bitrate="1500k",  # good balance; increase to 4000k for higher quality
        logger=logger,

    )

    return os.path.basename(output_path)
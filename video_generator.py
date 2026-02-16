# video_generator.py
from proglog import ProgressBarLogger

import re
from moviepy.config import change_settings

change_settings({
    "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
})

import os
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
    "resolution": (854, 480),  # change to 480p as (854, 480) for smaller file size
    "fps": 15, 
    "font_size": 40,
    "pip_size": (320, 180), # make it small and rectangular for better aesthetics
    "pip_opacity": 1.0,
    "font_path": r"D:\video_maker\fonts\NotoSansTelugu-Bold.ttf"
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
        font="fonts/NotoSansTelugu-Bold.ttf",
        fontsize=font_size,
        color=shadow_color,
        size=(text_width, None),
        method="caption",
        align="center",
    )

    main_clip = TextClip(
        text,
        font="fonts/NotoSansTelugu-Bold.ttf",
        fontsize=font_size,
        color=main_color,
        size=(text_width, None),
        method="caption",
        align="center",
    )

    # In the original code, 8 clips were created for the shadow, which was inefficient.
    # By creating a composite clip with just the main text and one shadow layer, performance is improved.
    text_clip = CompositeVideoClip(
        [
            shadow_clip.set_position((2, 2)),
            main_clip.set_position((0, 0)),
        ],
        size=(text_width, shadow_clip.h),
    ).set_position((side_margin, 0))

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

    try:
        pip = VideoFileClip(pip_path).without_audio()

        if pip.duration < duration:
            loops = int(duration / pip.duration) + 1
            pip = concatenate_videoclips([pip] * loops)
            print(f"🔄 PIP looped {loops} times")

        pip = pip.subclip(0, duration).resize(CONFIG["pip_size"])

        pip_x = (CONFIG["resolution"][0] - CONFIG["pip_size"][0]) // 2
        pip_y = (CONFIG["resolution"][1] - CONFIG["pip_size"][1]) // 2

        pip = pip.set_position((pip_x, pip_y)).set_opacity(CONFIG["pip_opacity"])

        has_pip = True
        

    except Exception as e:
        print(f"⚠ PIP failed: {str(e)} → skipping")


    # ================= COMPOSITE MAIN =================
    print("🎨 Compositing layers...")

    layers = [background, text_clip]
    if has_pip:
        layers.insert(1, pip)  # PIP between background and text

    main_video = CompositeVideoClip(layers, size=CONFIG["resolution"])

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
        preset="veryfast",
        ffmpeg_params=["-crf", "28"],
        logger=logger,

    )

    return os.path.basename(output_path)
# video_generator.py - OPTIMIZED VERSION
from proglog import ProgressBarLogger
import re
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, ColorClip, CompositeVideoClip
from moviepy.config import change_settings

# ================= IMAGEMAGICK =================
if os.name == "nt":  # Windows
    change_settings({
        "IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.2-Q16-HDRI\magick.exe"
    })
else:
    import shutil
    _magick = "magick" if shutil.which("magick") else "convert"
    if not shutil.which("magick") and not shutil.which("convert"):
        raise EnvironmentError(
            "ImageMagick not found. Run: sudo apt install -y imagemagick"
        )
    change_settings({"IMAGEMAGICK_BINARY": _magick})

# ================= CONFIG =================
CONFIG = {
    "resolution": (854, 480),
    "fps": 20,
    "font_path": "fonts/NotoSansTelugu-Bold.ttf"
}


def make_text_image(text, font_path, font_size, color, width):
    """
    Render text using Pillow directly — correct Telugu glyph shaping.
    Returns a PIL Image in RGBA mode.
    """
    font = ImageFont.truetype(font_path, font_size)

    # Word wrap to fit within width
    words = text.split()
    lines = []
    current_line = ""

    temp_img = Image.new("RGBA", (width, 100))
    temp_draw = ImageDraw.Draw(temp_img)

    for word in words:
        test_line = current_line + (" " if current_line else "") + word
        bbox = temp_draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    # Calculate total height
    line_height = font_size + 10
    total_height = line_height * len(lines) + 20

    # Draw on transparent background
    img = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Parse color
    try:
        if color.startswith("#"):
            r = int(color[1:3], 16)
            g = int(color[3:5], 16)
            b = int(color[5:7], 16)
            fill_color = (r, g, b, 255)
        else:
            temp = Image.new("RGB", (1, 1), color)
            r, g, b = temp.getpixel((0, 0))
            fill_color = (r, g, b, 255)
    except Exception:
        fill_color = (0, 0, 0, 255)

    y = 10
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) // 2
        draw.text((x, y), line, font=font, fill=fill_color)
        y += line_height

    return img


def generate_video(
    text,
    background_path,
    scroll_speed=50,
    font_size=40,
    main_color="black",
    progress_func=None,
    output_path="output/final_video.mp4",
):
    W, H = CONFIG["resolution"]

    # ================= TEXT CLEAN =================
    print("🖋️ Creating text clip with Pillow rendering...")
    text = re.sub(r'\s+', ' ', text).strip()

    side_margin = 10
    text_width = W - (side_margin * 2)

    # Render text to PIL image then convert to numpy RGBA array
    pil_text = make_text_image(text, CONFIG["font_path"], font_size, main_color, text_width)
    text_array = np.array(pil_text)  # shape: (text_height, text_width, 4) RGBA

    text_height = text_array.shape[0]
    duration = (text_height + H) / scroll_speed

    # Create MoviePy ImageClip from RGBA numpy array (supports transparency)
    text_clip = (
        ImageClip(text_array, ismask=False)
        .set_duration(duration)
        .set_position(lambda t: (side_margin, H - int(scroll_speed * t)))
    )

    print(f"✅ Text clip ready: {duration:.1f}s")

    # ================= BACKGROUND =================
    try:
        background = ImageClip(background_path)
        if background.size != CONFIG["resolution"]:
            background = background.resize(CONFIG["resolution"])
        background = background.set_duration(duration)
        print("✅ Background loaded")
    except Exception as e:
        print(f"⚠ Background failed: {e} → black background")
        background = ColorClip(CONFIG["resolution"], color=(0, 0, 0)).set_duration(duration)

    # ================= COMPOSITE =================
    print("🎨 Compositing main video...")
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
    print("💾 Exporting with optimized settings...")
    final_video.write_videofile(
        output_path,
        fps=CONFIG["fps"],
        codec="libx264",
        audio=False,
        threads=2,
        preset="ultrafast",
        ffmpeg_params=[
            "-crf", "26",
            "-movflags", "+faststart",
        ],
        logger=logger,
    )

    print("\n" + "=" * 50)
    print("✅ VIDEO COMPLETE!")
    print(f"📁 {output_path}")
    print(f"⏱️  {duration:.1f}s")
    print("=" * 50)

    if progress_func:
        progress_func(100)

    return os.path.basename(output_path)
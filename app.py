import os
import re
import time
import threading
import queue
from flask import Flask, render_template, request, jsonify, send_file
from video_generator import generate_video
from werkzeug.utils import secure_filename

app = Flask(__name__)

# -------- SECURITY SETTINGS --------
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB limit for uploads

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
# -----------------------------------

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------- PROGRESS TRACKING --------
progress_status = {}

def update_progress(job_id, value):
    progress_status[job_id] = value
# -----------------------------------

# -------- FILE CLEANUP --------
VIDEO_MAX_AGE_SECONDS = 60 * 30  # delete output videos older than 30 min
CLEANUP_INTERVAL = 60            # scan every 60 seconds

def safe_remove(path):
    """Delete a file silently if it still exists."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Deleted: {path}")
    except Exception as e:
        print(f"Delete failed for {path}: {e}")

def cleanup_old_videos():
    """
    Background thread: every CLEANUP_INTERVAL seconds, walk OUTPUT_FOLDER
    and delete any .mp4 whose last-modified time exceeds VIDEO_MAX_AGE_SECONDS.
    Runs once immediately on startup to clear leftovers from previous runs.
    """
    while True:
        now = time.time()
        try:
            for fname in os.listdir(OUTPUT_FOLDER):
                if not fname.endswith(".mp4"):
                    continue
                fpath = os.path.join(OUTPUT_FOLDER, fname)
                try:
                    age = now - os.path.getmtime(fpath)
                    if age > VIDEO_MAX_AGE_SECONDS:
                        safe_remove(fpath)
                except Exception as e:
                    print(f"Cleanup check failed for {fpath}: {e}")
        except Exception as e:
            print(f"Cleanup scan failed: {e}")

        time.sleep(CLEANUP_INTERVAL)

threading.Thread(target=cleanup_old_videos, daemon=True).start()
# ------------------------------


# -------- VIDEO QUEUE SYSTEM --------
video_queue = queue.Queue()

def worker():
    while True:
        try:
            job = video_queue.get()

            if job is None:
                continue

            job_id = job["job_id"]
            text = job["text"]
            background_path = job["background_path"]
            scroll_speed = job["scroll_speed"]
            font_size = job["font_size"]
            main_color = job["main_color"]
            output_path = job["output_path"]

            generate_video(
                text=text,
                background_path=background_path,
                scroll_speed=scroll_speed,
                font_size=font_size,
                main_color=main_color,
                progress_func=lambda v: update_progress(job_id, v),
                output_path=output_path
            )

            # Delete uploaded background immediately after encoding
            safe_remove(background_path)

            update_progress(job_id, 100)

            # CHANGE 1: Clean up progress_status after 5 minutes so the dict
            # doesn't grow forever and leak memory on a long-running AWS server.
            threading.Timer(300, lambda jid=job_id: progress_status.pop(jid, None)).start()

        except Exception as e:
            print(f"Worker error: {e}")

        finally:
            video_queue.task_done()

for _ in range(2):
    threading.Thread(target=worker, daemon=True).start()
# -----------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    print("Received generation request")

    job_id = os.urandom(6).hex()
    update_progress(job_id, 0)

    # CHANGE 2: Cap text length to prevent a huge payload from freezing
    # the worker for hours on a small AWS instance.
    text = request.form.get("text", "")[:15000]
    if not text.strip():
        return "Text is required", 400

    # CHANGE 3: Clamp scroll_speed and font_size to safe ranges so a
    # crafted request can't pass extreme values to ffmpeg / ImageMagick.
    try:
        scroll_speed = max(10, min(300, int(request.form["scroll_speed"])))
        font_size    = max(10, min(120, int(request.form["font_size"])))
    except (ValueError, KeyError):
        return "Invalid scroll_speed or font_size", 400

    # CHANGE 4: Validate main_color — only allow #RRGGBB hex or plain colour
    # names (e.g. "black", "white"). Rejects anything that could be used as
    # an injection payload against ImageMagick.
    main_color = request.form.get("main_color", "#000000").strip()
    if not re.match(r'^#[0-9a-fA-F]{6}$|^[a-zA-Z]+$', main_color):
        return "Invalid color value", 400

    background_file = request.files.get("background")

    if not background_file or background_file.filename == "":
        return "No file selected", 400

    if not allowed_file(background_file.filename):
        return "Only image files allowed.", 400

    # SAFE RANDOM FILENAME
    random_name = os.urandom(6).hex()
    filename = secure_filename(background_file.filename)
    extension = filename.rsplit(".", 1)[-1]

    bg_filename = f"bg_{random_name}.{extension}"
    bg_path = os.path.join(UPLOAD_FOLDER, bg_filename)

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    background_file.save(bg_path)

    output_filename = f"{job_id}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    job = {
        "job_id": job_id,
        "text": text,
        "background_path": bg_path,
        "scroll_speed": scroll_speed,
        "font_size": font_size,
        "main_color": main_color,
        "output_path": output_path
    }

    video_queue.put(job)

    return jsonify({
        "file": output_filename,
        "job_id": job_id
    })


@app.route("/download/<filename>")
def download(filename):

    safe_name = secure_filename(filename)
    path = os.path.join(OUTPUT_FOLDER, safe_name)

    if not os.path.exists(path):
        return jsonify({"error": "File not ready yet"}), 404

    return send_file(
        path,
        as_attachment=True,
        download_name="generated_video.mp4",
        mimetype="video/mp4"
    )


@app.route("/progress/<job_id>")
def progress(job_id):
    percent = progress_status.get(job_id, 0)
    return jsonify({"percent": percent})


port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=False)
# app.py
import os
import time
import threading
import queue
import webbrowser
from flask import Flask, render_template, request, jsonify, send_file
from video_generator import generate_video
from werkzeug.utils import secure_filename


app = Flask(__name__)

# -------- SECURITY SETTINGS --------
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
# -----------------------------------

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# -------- PROGRESS TRACKING --------
progress_status = {"percent": 0}

def update_progress(value):
    progress_status["percent"] = value
# -----------------------------------


# -------- VIDEO QUEUE SYSTEM --------
video_queue = queue.Queue()

def worker():
    while True:
        job = video_queue.get()

        if job is None:
            break

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
            progress_func=update_progress,
            output_path=output_path
        )

        os.remove(background_path)

        time.sleep(1)
        progress_status["percent"] = 100

        clean_old_videos(OUTPUT_FOLDER)  

        video_queue.task_done()

threading.Thread(target=worker, daemon=True).start()
# -----------------------------------


# -------- CLEAN OLD VIDEOS --------
def clean_old_videos(folder, max_files=10):

    files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.endswith(".mp4")
    ]

    files.sort(key=os.path.getmtime)

    while len(files) > max_files:

        oldest = files.pop(0)

        try:
            os.remove(oldest)
            print(f"🗑 Deleted old video: {oldest}")
        except Exception as e:
            print(f"❌ Could not delete {oldest}: {e}")
# ----------------------------------



@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    progress_status["percent"] = 0

    text = request.form["text"]
    scroll_speed = int(request.form["scroll_speed"])
    font_size = int(request.form["font_size"])
    main_color = request.form["main_color"]

    background_file = request.files["background"]

    if background_file.filename == "":
        return "No file selected", 400

    if not allowed_file(background_file.filename):
        return "Only image files (jpg, jpeg, png, webp) are allowed.", 400

    filename = secure_filename(background_file.filename)
    bg_path = os.path.join(UPLOAD_FOLDER, filename)
    background_file.save(bg_path)

    output_filename = f"final_{os.urandom(4).hex()}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    job = {
        "text": text,
        "background_path": bg_path,
        "scroll_speed": scroll_speed,
        "font_size": font_size,
        "main_color": main_color,
        "output_path": output_path
    }

    video_queue.put(job)

    return jsonify({"file": output_filename})


@app.route("/download/<filename>")
def download(filename):

    path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(path):
        return jsonify({"error": "File not ready yet"}), 404

    return send_file(
        path,
        as_attachment=True,
        download_name="generated_video.mp4",
        mimetype="video/mp4"
    )


@app.route("/progress")
def progress():
    return jsonify(progress_status)


port = int(os.environ.get("PORT", 5000))

def open_browser():
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":

    threading.Timer(2, open_browser).start()

    app.run(host="0.0.0.0", port=5000, debug=False)


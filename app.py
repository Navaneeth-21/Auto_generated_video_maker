import os
import time
import threading
import queue
from flask import Flask, render_template, request, jsonify, send_file, abort
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
progress_status = {}

def update_progress(job_id, value):
    progress_status[job_id] = value
# -----------------------------------


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

            # delete uploaded background
            if os.path.exists(background_path):
                os.remove(background_path)

            progress_status["percent"] = 100

        except Exception as e:
            print("❌ Worker error:", e)

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

    job_id = os.urandom(6).hex()
    progress_status["percent"] = 0

    text = request.form["text"]
    scroll_speed = int(request.form["scroll_speed"])
    font_size = int(request.form["font_size"])
    main_color = request.form["main_color"]

    background_file = request.files["background"]

    if background_file.filename == "":
        return "No file selected", 400

    if not allowed_file(background_file.filename):
        return "Only image files allowed.", 400

    # SAFE RANDOM FILENAME
    random_name = os.urandom(6).hex()
    filename = secure_filename(background_file.filename)
    extension = filename.split(".")[-1]

    bg_filename = f"bg_{random_name}.{extension}"
    bg_path = os.path.join(UPLOAD_FOLDER, bg_filename)

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
    
    def delayed_delete(file_path):

        max_wait = 60 * 60 # 1 hour
        waited = 0

        while waited < max_wait:

            # if file no longer exists stop
            if not os.path.exists(file_path):
                return

            time.sleep(10)
            waited += 10

        try:
            os.remove(file_path)
            print(f"🗑 Deleted video: {file_path}")
        except Exception as e:
            print("Delete failed:", e)

    threading.Thread(target=delayed_delete, args=(path,), daemon=True).start()
        

    response = send_file(
        path,
        as_attachment=True,
        download_name="generated_video.mp4",
        mimetype="video/mp4"
    )

    @response.call_on_close
    def delete_file():
        print("DELETE FUNCTION CALLED")
        try:
            os.remove(path)
            print(f"🗑 Deleted video after download: {path}")
        except Exception as e:
            print(f"Delete failed: {e}")

    return response

@app.route("/progress/<job_id>")
def progress(job_id):
    percent = progress_status.get(job_id, 0)
    return jsonify({"percent": percent})


port = int(os.environ.get("PORT", 5000))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=port, debug=False)
# app.py
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from video_generator import generate_video

app = Flask(__name__)

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/output"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ---------------- PROGRESS TRACKING ----------------
progress_status = {
    "percent": 0,
}

def update_progress(value):
    progress_status["percent"] = value
# ---------------------------------------------------


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    global progress_status

    # Reset progress
    progress_status["percent"] = 0

    text = request.form["text"]
    scroll_speed = int(request.form["scroll_speed"])
    font_size = int(request.form["font_size"])
    main_color = request.form["main_color"]

    # ---------------- UPDATED FILE INPUTS ----------------
    background_file = request.files["background"]
    intro1_file = request.files["intro1"]
    intro2_file = request.files["intro2"]

    bg_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    intro1_path = os.path.join(UPLOAD_FOLDER, intro1_file.filename)
    intro2_path = os.path.join(UPLOAD_FOLDER, intro2_file.filename)

    background_file.save(bg_path)
    intro1_file.save(intro1_path)
    intro2_file.save(intro2_path)
    # ------------------------------------------------------

    output_filename = f"final_{os.urandom(4).hex()}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Call generator
    generate_video(
        text=text,
        background_path=bg_path,
        intro1_path=intro1_path,
        intro2_path=intro2_path,
        scroll_speed=scroll_speed,
        font_size=font_size,
        main_color=main_color,
        progress_func=update_progress,
        output_path=output_path
    )

    # Ensure final state
    progress_status["percent"] = 100

    return jsonify({"status": "done", "file": output_filename})


# -------- PROGRESS ENDPOINT --------
@app.route("/progress")
def progress():
    return jsonify(progress_status)
# -----------------------------------


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)


port = int(os.environ.get("PORT", 5000))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

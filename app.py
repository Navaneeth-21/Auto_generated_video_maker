# app.py
import os
from flask import Flask, render_template, request, jsonify, send_file
from video_generator import generate_video
import webbrowser
import threading

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "output"

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

    # Save background image
    background_file = request.files["background"]
    bg_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    background_file.save(bg_path)

    output_filename = f"final_{os.urandom(4).hex()}.mp4"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Generate video
    generate_video(
        text=text,
        background_path=bg_path,
        scroll_speed=scroll_speed,
        font_size=font_size,
        main_color=main_color,
        progress_func=update_progress,
        output_path=output_path
    )

    # Ensure progress complete
    progress_status["percent"] = 100

    # 🔹 SEND VIDEO DIRECTLY (AUTO DOWNLOAD)
    return send_file(
        output_path,
        as_attachment=True,
        download_name="generated_video.mp4",
        mimetype="video/mp4"
    )


# -------- PROGRESS ENDPOINT --------
@app.route("/progress")
def progress():
    return jsonify(progress_status)
# -----------------------------------


port = int(os.environ.get("PORT", 5000))

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    # open browser automatically after 2 seconds
    threading.Timer(2, open_browser).start()

    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
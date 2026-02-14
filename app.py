# app.py
import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from video_generator import generate_video

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
    shadow_color = request.form["shadow_color"]


    # Uploaded files
    background_file = request.files["background"]
    pip_file = request.files["pip"]
    intro_file = request.files["intro"] 

    bg_path = os.path.join(UPLOAD_FOLDER, background_file.filename)
    pip_path = os.path.join(UPLOAD_FOLDER, pip_file.filename)
    intro_path = os.path.join(UPLOAD_FOLDER, intro_file.filename)

    background_file.save(bg_path)
    pip_file.save(pip_path)
    intro_file.save(intro_path)

    output_filename = f"final_{os.urandom(4).hex()}.mp4" 
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    # Call generator with log function
    generate_video(
        text=text,
        background_path=bg_path,
        pip_path=pip_path,
        intro_path=intro_path,
        scroll_speed=scroll_speed,
        font_size=font_size,
        main_color=main_color,
        shadow_color=shadow_color,
        progress_func=update_progress,
        output_path=output_path
    )

    # Ensure final state
    progress_status["percent"] = 100

    return jsonify({"status": "done", "file": output_filename})



# -------- NEW PROGRESS ENDPOINT --------
@app.route("/progress")
def progress():
    return jsonify(progress_status)
# ---------------------------------------


@app.route("/download/<filename>")
def download(filename):
    return send_from_directory(OUTPUT_FOLDER, filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
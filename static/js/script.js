// static/js/script.js

let generatedFile = null;
let jobId = null;

document.getElementById("videoForm").addEventListener("submit", function(e) {

    e.preventDefault();

    generatedFile = null;
    jobId = null;

    const loader = document.getElementById("loader");
    const button = this.querySelector("button");

    loader.style.display = "block";

    document.getElementById("progress-container").style.display = "block";
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("progress-text").innerText = "0%";

    // Disable button to prevent duplicate submissions
    button.disabled = true;

    const formData = new FormData(this);

    fetch("/generate", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        generatedFile = data.file;
        jobId = data.job_id;

        pollProgress(button);

    })
    .catch(err => {

        console.error(err);
        alert("Error generating video.");

        loader.style.display = "none";
        button.disabled = false;

    });

});


function pollProgress(button) {

    if (!jobId) return;

    fetch("/progress/" + jobId)
        .then(res => res.json())
        .then(data => {

            const percent = data.percent || 0;

            document.getElementById("progress-fill").style.width = percent + "%";
            document.getElementById("progress-text").innerText = percent + "%";

            if (percent >= 100) {

                const progressFill = document.getElementById("progress-fill");

                progressFill.classList.add("success-complete");

                setTimeout(() => {

                    document.getElementById("progress-container").style.display = "none";
                    progressFill.classList.remove("success-complete");
                    document.getElementById("loader").style.display = "none";

                    button.disabled = false;

                    // Auto download
                    if (generatedFile) {
                        window.location.href = "/download/" + generatedFile;
                    }

                }, 4000);

                return;
            }

            setTimeout(() => pollProgress(button), 1000);

        })
        .catch(err => {

            console.error("Progress polling failed:", err);

            // Retry polling after delay
            setTimeout(() => pollProgress(button), 2000);

        });

}
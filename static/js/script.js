// static/js/script.js

let generatedFile = null;

document.getElementById("videoForm").addEventListener("submit", function(e) {

    e.preventDefault(); // stop normal form submit

    const loader = document.getElementById("loader");

    loader.style.display = "block";

    document.getElementById("progress-container").style.display = "block";
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("progress-text").innerText = "0%";

    const formData = new FormData(this);

    fetch("/generate", {
        method: "POST",
        body: formData
    })
    .then(res => res.json())
    .then(data => {

        generatedFile = data.file;

        pollProgress();

    })
    .catch(err => {
        console.error(err);
        alert("Error generating video.");
    });

});


function pollProgress() {

    fetch("/progress")
        .then(res => res.json())
        .then(data => {

            const percent = data.percent;

            document.getElementById("progress-fill").style.width = percent + "%";
            document.getElementById("progress-text").innerText = percent + "%";

            if (percent >= 100) {

                const progressFill = document.getElementById("progress-fill");

                progressFill.classList.add("success-complete");

                setTimeout(() => {

                    document.getElementById("progress-container").style.display = "none";
                    progressFill.classList.remove("success-complete");
                    document.getElementById("loader").style.display = "none";

                    // 🔥 AUTO DOWNLOAD
                    if (generatedFile) {
                        window.location.href = "/download/" + generatedFile;
                    }

                }, 1500);

                return;
            }

            setTimeout(pollProgress, 1000);

        });

}
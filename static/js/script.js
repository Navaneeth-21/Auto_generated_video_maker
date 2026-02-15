document.getElementById("videoForm").addEventListener("submit", function(e) {
    e.preventDefault();

    const loader = document.getElementById("loader");
    const downloadBox = document.getElementById("download");

    loader.style.display = "block";
    downloadBox.innerHTML = "";

    document.getElementById("progress-container").style.display = "block";
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("progress-text").innerText = "0%";

    const formData = new FormData(this);

    fetch("/generate", {
        method: "POST",
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        loader.style.display = "none";

        downloadBox.innerHTML =
            `<a href="/download/${data.file}">⬇ Download Video</a>`;
    });

    pollProgress();
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
                }, 5000);
                return;
            }

            if (percent < 100) {
                setTimeout(pollProgress, 1000);
            }
        });
}

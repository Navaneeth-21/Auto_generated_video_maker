// static/js/script.js

document.getElementById("videoForm").addEventListener("submit", function() {

    const loader = document.getElementById("loader");

    loader.style.display = "block";

    document.getElementById("progress-container").style.display = "block";
    document.getElementById("progress-fill").style.width = "0%";
    document.getElementById("progress-text").innerText = "0%";

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
                    document.getElementById("loader").style.display = "none";

                }, 3000);

                return;
            }

            setTimeout(pollProgress, 1000);

        });

}
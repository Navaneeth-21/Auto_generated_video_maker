// ===== CHAR COUNTER =====
const CHAR_LIMIT   = 50000;
const storyText    = document.getElementById('storyText');
const charCount    = document.getElementById('charCount');
const charCounter  = document.getElementById('charCounter');
const charWarning  = document.getElementById('charWarning');
const generateBtn  = document.getElementById('generateBtn');

function updateCharCount() {
    const len = storyText.value.length;
    charCount.textContent = len.toLocaleString();
    if (len > CHAR_LIMIT) {
        charCounter.classList.add('over-limit');
        charWarning.classList.add('visible');
        storyText.classList.add('over-limit');
        generateBtn.classList.add('over-limit');
        generateBtn.disabled = true;
    } else {
        charCounter.classList.remove('over-limit');
        charWarning.classList.remove('visible');
        storyText.classList.remove('over-limit');
        generateBtn.classList.remove('over-limit');
        if (!generateBtn.classList.contains('generating')) {
            generateBtn.disabled = false;
        }
    }
}
storyText.addEventListener('input', updateCharCount);

// ===== SLIDERS =====
const scrollSpeed = document.getElementById('scrollSpeed');
const scrollVal   = document.getElementById('scrollVal');
const fontSize    = document.getElementById('fontSize');
const fontVal     = document.getElementById('fontVal');

function updateSliderTrack(slider) {
    const pct = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
    slider.style.background = `linear-gradient(to right, #d4af37 ${pct}%, #111827 ${pct}%)`;
}

scrollSpeed.addEventListener('input', () => { scrollVal.textContent = scrollSpeed.value; updateSliderTrack(scrollSpeed); });
fontSize.addEventListener('input',   () => { fontVal.textContent   = fontSize.value;    updateSliderTrack(fontSize); });
updateSliderTrack(scrollSpeed);
updateSliderTrack(fontSize);

// ===== COLOR PRESETS =====
const colorPicker = document.getElementById('colorPicker');
const presetDots  = document.querySelectorAll('.preset-dot');

presetDots.forEach(dot => {
    dot.addEventListener('click', () => {
        colorPicker.value = dot.dataset.color;
        presetDots.forEach(d => d.classList.remove('active'));
        dot.classList.add('active');
    });
});
colorPicker.addEventListener('input', () => presetDots.forEach(d => d.classList.remove('active')));

// ===== FILE DROP =====
const bgFile        = document.getElementById('bgFile');
const fileDropInner = document.getElementById('fileDropInner');
const fileDrop      = document.getElementById('fileDrop');

bgFile.addEventListener('change', () => {
    if (bgFile.files.length > 0) {
        fileDropInner.classList.add('has-file');
        fileDropInner.querySelector('p').textContent = bgFile.files[0].name;
    }
});

fileDrop.addEventListener('dragover',  (e) => { e.preventDefault(); fileDropInner.classList.add('dragover'); });
fileDrop.addEventListener('dragleave', ()  => fileDropInner.classList.remove('dragover'));
fileDrop.addEventListener('drop', (e) => {
    e.preventDefault();
    fileDropInner.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        bgFile.files = files;
        fileDropInner.classList.add('has-file');
        fileDropInner.querySelector('p').textContent = files[0].name;
    }
});

// ===== FORM SUBMIT =====
let generatedFile = null;
let jobId         = null;

document.getElementById('videoForm').addEventListener('submit', function(e) {
    e.preventDefault();
    if (storyText.value.length > CHAR_LIMIT) return;

    generatedFile = null;
    jobId         = null;

    // Show progress, hide video ready
    document.getElementById('progressSection').style.display = 'block';
    document.getElementById('videoReady').style.display      = 'none';
    document.getElementById('progressFill').style.width      = '0%';
    document.getElementById('progressPct').textContent       = '0%';

    // Button generating state
    generateBtn.disabled = true;
    generateBtn.classList.add('generating');
    generateBtn.querySelector('.btn-text').textContent = 'GENERATING...';

    const formData = new FormData(this);

    fetch('/generate', { method: 'POST', body: formData })
        .then(res => res.json())
        .then(data => {
            generatedFile = data.file;
            jobId         = data.job_id;
            pollProgress();
        })
        .catch(err => {
            console.error(err);
            alert('Error generating video.');
            resetBtn();
            document.getElementById('progressSection').style.display = 'none';
        });
});

function pollProgress() {
    if (!jobId) return;

    fetch('/progress/' + jobId)
        .then(res => res.json())
        .then(data => {
            const percent = data.percent || 0;
            document.getElementById('progressFill').style.width = percent + '%';
            document.getElementById('progressPct').textContent  = percent + '%';

            if (percent >= 100) {
                setTimeout(() => {
                    document.getElementById('progressSection').style.display = 'none';
                    showVideoReady();
                }, 800);
                return;
            }
            setTimeout(pollProgress, 1000);
        })
        .catch(err => {
            console.error('Polling error:', err);
            setTimeout(pollProgress, 2000);
        });
}

function showVideoReady() {
    const videoReady   = document.getElementById('videoReady');
    const videoPreview = document.getElementById('videoPreview');
    const downloadBtn  = document.getElementById('downloadBtn');
    const downloadUrl  = '/download/' + generatedFile;

    // AUTO DOWNLOAD — mandatory, triggers immediately
    window.location.href = downloadUrl;

    // Set video source for preview
    videoPreview.src = downloadUrl;

    // Set download button href
    downloadBtn.href = downloadUrl;

    videoReady.style.display = 'block';
    videoReady.scrollIntoView({ behavior: 'smooth', block: 'start' });

    resetBtn();
}

// ===== NEW VIDEO BUTTON =====
document.getElementById('newVideoBtn').addEventListener('click', () => {
    document.getElementById('videoReady').style.display = 'none';
    document.getElementById('videoForm').reset();
    document.getElementById('progressSection').style.display = 'none';

    // Reset char counter
    charCount.textContent = '0';
    charCounter.classList.remove('over-limit');
    charWarning.classList.remove('visible');
    storyText.classList.remove('over-limit');

    // Reset file drop
    fileDropInner.classList.remove('has-file');
    fileDropInner.querySelector('p').innerHTML = 'Drag & drop or <span class="browse-link">browse</span>';

    // Reset sliders display
    scrollVal.textContent = scrollSpeed.value;
    fontVal.textContent   = fontSize.value;

    // Reset color presets
    presetDots.forEach(d => d.classList.remove('active'));
    presetDots[0].classList.add('active');

    window.scrollTo({ top: 0, behavior: 'smooth' });
});

function resetBtn() {
    generateBtn.disabled = false;
    generateBtn.classList.remove('generating', 'over-limit');
    generateBtn.querySelector('.btn-text').textContent = 'GENERATE VIDEO';
}
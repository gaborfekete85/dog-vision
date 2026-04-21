// Dog Vision frontend
// - Browse an image file
// - POST it to /api/predict
// - Render top breed + all probability bars

const fileInput   = document.getElementById("file-input");
const previewWrap = document.getElementById("preview-wrap");
const previewImg  = document.getElementById("preview");
const fileNameEl  = document.getElementById("file-name");
const predictBtn  = document.getElementById("predict-btn");
const clearBtn    = document.getElementById("clear-btn");
const statusEl    = document.getElementById("status");
const resultsEl   = document.getElementById("results");
const topBreed    = document.getElementById("top-breed");
const topConf     = document.getElementById("top-confidence");
const chartEl     = document.getElementById("chart");
const showAllEl   = document.getElementById("show-all");
const healthEl    = document.getElementById("health");

let selectedFile  = null;
let lastPredictions = null;

// ---- Health check (shows the loaded model in the footer) ------------------
fetch("/api/health")
  .then(r => r.json())
  .then(j => {
    healthEl.textContent = `model: ${j.model} · ${j.num_breeds} breeds`;
  })
  .catch(() => { healthEl.textContent = "backend offline"; });

// ---- File selection -------------------------------------------------------
fileInput.addEventListener("change", (e) => {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  selectedFile = f;
  fileNameEl.textContent = f.name;

  const reader = new FileReader();
  reader.onload = () => {
    previewImg.src = reader.result;
    previewWrap.classList.remove("hidden");
    predictBtn.disabled = false;
    setStatus("");                // clear any error
    resultsEl.classList.add("hidden");
  };
  reader.readAsDataURL(f);
});

clearBtn.addEventListener("click", () => {
  selectedFile = null;
  fileInput.value = "";
  previewImg.src = "";
  previewWrap.classList.add("hidden");
  predictBtn.disabled = true;
  resultsEl.classList.add("hidden");
  setStatus("");
});

// ---- Predict --------------------------------------------------------------
predictBtn.addEventListener("click", async () => {
  if (!selectedFile) return;
  predictBtn.disabled = true;
  setStatus("Running the model… this can take a few seconds on first run.");

  const fd = new FormData();
  fd.append("image", selectedFile);

  try {
    const res = await fetch("/api/predict", { method: "POST", body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderResults(data);
    setStatus("");
  } catch (err) {
    setStatus(err.message || "Prediction failed", true);
  } finally {
    predictBtn.disabled = false;
  }
});

// ---- Rendering ------------------------------------------------------------
function renderResults(data) {
  lastPredictions = data.predictions;
  topBreed.textContent = humanize(data.predicted_breed);
  topConf.textContent  = `confidence: ${(data.confidence * 100).toFixed(2)}%`;
  drawChart();
  resultsEl.classList.remove("hidden");
  resultsEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
}

function drawChart() {
  if (!lastPredictions) return;
  const all = showAllEl.checked;
  const rows = all ? lastPredictions : lastPredictions.slice(0, 15);

  chartEl.innerHTML = "";
  rows.forEach((row, i) => {
    const r = document.createElement("div");
    r.className = "bar-row" + (i === 0 ? " top" : "");
    r.innerHTML = `
      <span class="bar-label" title="${row.breed}">${humanize(row.breed)}</span>
      <span class="bar-track"><span class="bar-fill" style="width:${Math.max(row.probability * 100, 0.5)}%"></span></span>
      <span class="bar-value">${(row.probability * 100).toFixed(2)}%</span>
    `;
    chartEl.appendChild(r);
  });
}

showAllEl.addEventListener("change", drawChart);

// ---- Helpers --------------------------------------------------------------
function humanize(breed) {
  return String(breed).replace(/_/g, " ");
}

function setStatus(msg, isError = false) {
  if (!msg) {
    statusEl.classList.add("hidden");
    statusEl.classList.remove("error");
    statusEl.textContent = "";
    return;
  }
  statusEl.classList.remove("hidden");
  statusEl.classList.toggle("error", isError);
  statusEl.textContent = msg;
}

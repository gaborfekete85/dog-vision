"""
Dog Vision — Flask backend.

Loads the MobileNetV2 model trained in dog_vision.ipynb, accepts an uploaded
image from the frontend, preprocesses it identically to the notebook
(decode_jpeg -> float32 [0,1] -> resize 224x224), runs inference, and returns
the predicted breed plus the probability for every one of the 120 breeds.

Run (from this app/ directory):
    pip install -r requirements.txt
    python app.py

Then open http://localhost:5001 in your browser.
"""

import os
import io
import uuid
import logging
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image
from flask import Flask, jsonify, request, render_template, send_from_directory

import tensorflow as tf
import tensorflow_hub as hub


# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent  # /.../dog-vision

# The dataset ships in drive/MyDrive/ to mirror the Google Drive layout from
# the original Colab notebook.
DRIVE_DIR = PROJECT_DIR / "drive" / "MyDrive"
LABELS_CSV = DRIVE_DIR / "labels.csv"
MODELS_DIR = DRIVE_DIR / "models"

# Pick the latest "full-image-set" model (trained on the full 10k+ image
# dataset -> higher accuracy than the 1000-image debug models). If a specific
# model path is supplied via the DOG_VISION_MODEL env var, use that instead.
DEFAULT_MODEL = (
    MODELS_DIR / "20260216-16481771260506-full-image-set-mobilenetv2-Adam.h5"
)
MODEL_PATH = Path(os.environ.get("DOG_VISION_MODEL", DEFAULT_MODEL))

IMG_SIZE = 224  # matches the notebook
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Cache the downloaded TF-Hub MobileNetV2 module here so subsequent app
# starts are instant and the user only needs internet the very first time.
HUB_CACHE = BASE_DIR / ".tfhub_cache"
HUB_CACHE.mkdir(exist_ok=True)
os.environ.setdefault("TFHUB_CACHE_DIR", str(HUB_CACHE))
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger("dog-vision")


# --------------------------------------------------------------------------- #
# One-time load: labels + model
# --------------------------------------------------------------------------- #

def load_unique_breeds() -> np.ndarray:
    """Reproduces `unique_breeds = np.unique(labels_csv['breed'].to_numpy())`
    from the notebook so label indices line up with the model's output units."""
    if not LABELS_CSV.exists():
        raise FileNotFoundError(
            f"labels.csv not found at {LABELS_CSV}. "
            "The app expects the dataset at drive/MyDrive/ as in the notebook."
        )
    labels_csv = pd.read_csv(LABELS_CSV)
    return np.unique(labels_csv["breed"].to_numpy())


def load_trained_model(model_path: Path) -> tf.keras.Model:
    """Loads the .h5 model saved by the notebook. Because it contains a
    `tensorflow_hub.KerasLayer`, we must pass it in via custom_objects."""
    if not model_path.exists():
        raise FileNotFoundError(
            f"Model file not found: {model_path}\n"
            f"Available models in {MODELS_DIR}:\n  "
            + "\n  ".join(sorted(p.name for p in MODELS_DIR.glob('*.h5')))
        )
    log.info("Loading model from %s", model_path)
    try:
        return tf.keras.models.load_model(
            str(model_path),
            custom_objects={"KerasLayer": hub.KerasLayer},
        )
    except Exception as exc:
        msg = str(exc)
        if "urlopen" in msg or "403" in msg or "Tunnel" in msg or "Forbidden" in msg:
            raise RuntimeError(
                "Could not download the MobileNetV2 module from tfhub.dev. "
                "The first run needs internet access so TensorFlow Hub can fetch "
                "https://tfhub.dev/google/imagenet/mobilenet_v2_130_224/classification/4 "
                f"into {HUB_CACHE}. Once cached, subsequent runs work offline."
            ) from exc
        raise


log.info("Reading breeds from %s", LABELS_CSV)
UNIQUE_BREEDS = load_unique_breeds()
log.info("Loaded %d unique breeds", len(UNIQUE_BREEDS))

MODEL = load_trained_model(MODEL_PATH)
log.info("Model ready. Output units: %d", MODEL.output_shape[-1])

if MODEL.output_shape[-1] != len(UNIQUE_BREEDS):
    log.warning(
        "Model output (%d) != number of breeds (%d). Predictions may mismatch.",
        MODEL.output_shape[-1], len(UNIQUE_BREEDS),
    )


# --------------------------------------------------------------------------- #
# Preprocessing — mirrors notebook's process_image()
# --------------------------------------------------------------------------- #

def preprocess_image_bytes(raw: bytes) -> tf.Tensor:
    """Notebook equivalent:
        image = tf.io.read_file(path)
        image = tf.image.decode_jpeg(image, channels=3)
        image = tf.image.convert_image_dtype(image, tf.float32)  # 0..1
        image = tf.image.resize(image, [224, 224])
    We go via PIL first so PNG/WEBP/etc. also work, then follow the same
    channels=3 -> float32 [0,1] -> 224x224 shape.
    """
    pil = Image.open(io.BytesIO(raw)).convert("RGB")
    image = tf.convert_to_tensor(np.array(pil), dtype=tf.uint8)
    image = tf.image.convert_image_dtype(image, tf.float32)
    image = tf.image.resize(image, [IMG_SIZE, IMG_SIZE])
    return image


def predict(raw: bytes) -> dict:
    image = preprocess_image_bytes(raw)
    batch = tf.expand_dims(image, axis=0)              # [1, 224, 224, 3]
    probs = MODEL.predict(batch, verbose=0)[0]         # shape (120,)

    top_idx = int(np.argmax(probs))
    all_preds = [
        {"breed": breed, "probability": float(p)}
        for breed, p in zip(UNIQUE_BREEDS, probs)
    ]
    all_preds.sort(key=lambda x: x["probability"], reverse=True)

    return {
        "predicted_breed": str(UNIQUE_BREEDS[top_idx]),
        "confidence": float(probs[top_idx]),
        "predictions": all_preds,  # sorted high -> low, all 120
    }


# --------------------------------------------------------------------------- #
# Flask app
# --------------------------------------------------------------------------- #

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "model": MODEL_PATH.name,
        "num_breeds": len(UNIQUE_BREEDS),
    })


@app.get("/api/breeds")
def breeds():
    return jsonify({"breeds": [str(b) for b in UNIQUE_BREEDS]})


@app.post("/api/predict")
def api_predict():
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded under field 'image'."}), 400

    upload = request.files["image"]
    if not upload.filename:
        return jsonify({"error": "Empty filename."}), 400

    ext = Path(upload.filename).suffix.lower()
    if ext and ext not in ALLOWED_EXT:
        return jsonify({
            "error": f"Unsupported extension '{ext}'. Allowed: "
                     + ", ".join(sorted(ALLOWED_EXT))
        }), 400

    raw = upload.read()
    if not raw:
        return jsonify({"error": "Uploaded file is empty."}), 400

    # Save a copy so the frontend can show the exact image back to the user.
    safe_name = f"{uuid.uuid4().hex}{ext or '.img'}"
    saved_path = UPLOAD_DIR / safe_name
    saved_path.write_bytes(raw)

    try:
        result = predict(raw)
    except Exception as exc:
        log.exception("Prediction failed")
        return jsonify({"error": f"Prediction failed: {exc}"}), 500

    result["image_url"] = f"/uploads/{safe_name}"
    return jsonify(result)


@app.get("/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)


if __name__ == "__main__":
    # Disable the reloader so the model isn't loaded twice in dev.
    app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False)

# README.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Dog Vision is a Flask web application that uses a trained TensorFlow/Keras MobileNetV2 model to classify dog breeds from uploaded images. The model was trained on 120 dog breeds and can predict the breed with confidence scores.

## Architecture

### Model Loading & Inference Flow

The app follows a specific preprocessing pipeline that must match the training notebook:

1. **Model Loading** (app.py:84-108): Loads `.h5` model with `tensorflow_hub.KerasLayer` in `custom_objects`
2. **Preprocessing** (app.py:129-142):
   - PIL opens image → RGB conversion
   - TensorFlow converts to uint8 tensor → float32 [0,1] normalization
   - Resize to 224x224 (matches MobileNetV2 input size)
3. **Prediction** (app.py:145-161): Batch inference returns probabilities for all 120 breeds

**Critical**: The preprocessing MUST match the training notebook's `process_image()` function or predictions will be incorrect.

### Data Dependencies

The app expects this directory structure (mirrors Google Colab layout from training):

```
dog-vision/
├── app/                          # Flask application (this directory)
│   ├── app.py
│   ├── templates/
│   ├── static/
│   └── .tfhub_cache/             # Cached TensorFlow Hub modules
└── drive/MyDrive/                # Dataset (Google Drive layout)
    ├── labels.csv                # Breed labels (used to create unique_breeds array)
    └── models/                   # Trained .h5 models
        └── 20260216-16481771260506-full-image-set-mobilenetv2-Adam.h5
```

**Model Selection**: The app defaults to the latest "full-image-set" model (trained on 10k+ images). Override with `DOG_VISION_MODEL` environment variable.

**Label Alignment**: `unique_breeds` array is created via `np.unique(labels_csv['breed'].to_numpy())` to match the model's output units (120 classes). The order must be identical to training.

### Environment Requirements

- **TensorFlow 2.15.1**: Pinned to match training environment
- **Keras 2**: Uses legacy Keras (`TF_USE_LEGACY_KERAS=1`) for compatibility with saved `hub.KerasLayer`
- **TensorFlow Hub**: First run requires internet to download MobileNetV2 module to `.tfhub_cache/`
- **Python 3.11**: Recommended version

## Development Commands

### Local Development

```bash
# Run with automatic venv setup and dependency installation
./run.sh
```

This script:
- Creates `.venv/` virtualenv if missing (using `uv`)
- Installs requirements
- Sets `TF_USE_LEGACY_KERAS=1`
- Starts Flask on http://localhost:5001

**Manual run**:
```bash
source .venv/bin/activate
export TF_USE_LEGACY_KERAS=1
export TF_CPP_MIN_LOG_LEVEL=2  # suppress TF warnings
python app.py
```

### Docker Build & Run

```bash
# Build (from parent directory containing app/ and drive/)
docker build -t gabendockerzone/dog-vision:latest .

# Push to Docker Hub
docker push gabendockerzone/dog-vision:latest
```

**Important**: Docker build context must be the parent directory (dog-vision/) because the Dockerfile copies both `app/` and `drive/` directories.

## Kubernetes Deployment

### Quick Deploy

```bash
# One-command deploy: build, push, and upgrade Helm release
./redeploy.sh
```

### Manual Helm Operations

```bash
# Install NGINX Ingress Controller first
./setup-ingress.sh

# Create namespace
kubectl create namespace dog-vision

# Install chart
helm install dog-vision ./helm/dog-vision --namespace dog-vision

# Upgrade existing release
helm upgrade dog-vision ./helm/dog-vision --namespace dog-vision

# View deployment status
kubectl get pods -n dog-vision
kubectl logs -f -n dog-vision -l app=dog-vision
```

**Deployment details**:
- Namespace: `dog-vision`
- Ingress: `dog-vision.rewura.com` (requires DNS A record)
- Health checks: `/api/health` (liveness/readiness probes)
- Image: `gabendockerzone/dog-vision:latest`
- Resources: 100m-500m CPU, 256Mi-1Gi memory (configurable in values.yaml)

## API Endpoints

- `GET /` - Web UI (templates/index.html)
- `GET /api/health` - Health check (returns model name, breed count)
- `GET /api/breeds` - List all 120 breeds
- `POST /api/predict` - Upload image (multipart/form-data field: "image")
  - Returns: predicted breed, confidence, full probability distribution
  - Allowed formats: jpg, jpeg, png, bmp, gif, webp
  - Max size: 10 MB

## Key Implementation Details

### Model Version Compatibility

The model contains a `tensorflow_hub.KerasLayer` that references:
```
https://tfhub.dev/google/imagenet/mobilenet_v2_130_224/classification/4
```

This module is downloaded on first run and cached in `.tfhub_cache/`. The specific TensorFlow/Keras versions (2.15.1 / Keras 2) are required to load the saved model without conversion errors.

### Preprocessing Pipeline

The `preprocess_image_bytes()` function (app.py:129-142) must maintain exact parity with the training notebook:

1. PIL handles non-JPEG formats (PNG, WEBP, etc.)
2. Convert to RGB (ensures 3 channels)
3. tf.convert_to_tensor as uint8
4. tf.image.convert_image_dtype to float32 (scales to [0,1])
5. tf.image.resize to [224, 224]

**DO NOT** modify this pipeline without verifying against the training notebook's `process_image()` function.

### Upload Handling

Uploaded images are saved to `uploads/` directory with UUID-based names (app.py:212-214) so the frontend can display the exact image back to the user via `/uploads/<filename>`.

## Troubleshooting

### "Could not download MobileNetV2 module"

First run requires internet access to download the TensorFlow Hub module. Subsequent runs work offline once cached in `.tfhub_cache/`.

### "Model output != number of breeds" warning

The model's final dense layer should have 120 units matching the 120 unique breeds in labels.csv. If this warning appears, verify:
1. Correct model file is being loaded
2. labels.csv hasn't been modified
3. Model was trained on the same breed set

### Image Pull Errors in Kubernetes

Ensure Docker image exists:
```bash
docker pull gabendockerzone/dog-vision:latest
```

If repository is private, create `imagePullSecrets` (see KUBERNETES-DEPLOYMENT.md line 220-237).

### Ingress Not Accessible

1. Verify NGINX Ingress Controller has external IP:
   ```bash
   kubectl get svc -n ingress-nginx
   ```
2. Configure DNS A record: `dog-vision.rewura.com` → `<EXTERNAL_IP>`
3. Check ingress status:
   ```bash
   kubectl describe ingress dog-vision -n dog-vision
   ```

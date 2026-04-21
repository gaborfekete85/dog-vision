#!/usr/bin/env bash
# Convenience runner: creates a venv if missing, installs deps, launches Flask.
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "[run.sh] Creating virtualenv…"
  uv venv --python 3.11 .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

echo "[run.sh] Installing requirements…"
uv pip install -q -r requirements.txt --index-url https://pypi.org/simple

# Force Keras 2 so hub.KerasLayer loads cleanly in TF 2.15.
export TF_USE_LEGACY_KERAS=1
export TF_CPP_MIN_LOG_LEVEL=2   # hide TF info/warning noise
echo "[run.sh] Starting Dog Vision on http://localhost:5001"
python app.py

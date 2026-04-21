FROM python:3.11-slim

WORKDIR /project/app

# Install system dependencies if any are needed for OpenCV or Pillow
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libgl1-mesa-glx \
#     && rm -rf /var/lib/apt/lists/*

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app code
COPY app/ .

# Copy the drive directory (contains labels.csv and models)
COPY drive /project/drive

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py

EXPOSE 5001

CMD ["python", "app.py"]

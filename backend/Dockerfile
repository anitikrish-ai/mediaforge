# MediaForge backend — a real CV/ML workload (OpenCV, scikit-image, ONNX
# inference, yt-dlp + ffmpeg muxing). This does not fit Vercel's serverless
# Python function size cap (500MB) or its lack of a system ffmpeg binary, so
# it's deployed as a container instead (Railway, Render, Fly.io, Cloud Run —
# anything that builds from a Dockerfile). Only the static frontend lives on
# Vercel; see /vercel.json and README.md.

FROM python:3.12-slim

# ffmpeg: required at runtime by yt-dlp for audio extraction / stream muxing.
# libgl1 + libglib2.0-0: OpenCV's shared-lib runtime deps (opencv-python-headless
# still dlopens a few libGL/libglib symbols even without GUI support).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway/Render/Fly all inject $PORT and expect the app to bind to it.
ENV PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]

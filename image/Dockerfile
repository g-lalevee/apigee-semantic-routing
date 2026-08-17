# -------------------------------------------------------------
# Production Dockerfile for Google Cloud Run
# Base: python:3.11-slim
# -------------------------------------------------------------
FROM python:3.11-slim

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FASTEMBED_CACHE_PATH=/app/model_cache \
    EMBEDDING_MODEL_NAME="BAAI/bge-small-en-v1.5" \
    PORT=8080

WORKDIR /app

# Install minimal OS build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download and bake model weights into the image
COPY preload_models.py .
RUN python preload_models.py && rm preload_models.py

# Copy application source code
COPY main.py .

# Security: Create and switch to non-root user
RUN groupadd -r appgroup && useradd -r -g appgroup -u 10001 appuser \
    && chown -R appuser:appgroup /app

USER appuser

# Healthcheck for container runtime monitoring
HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/healthz || exit 1

# Expose standard Cloud Run port
EXPOSE 8080

# Start Uvicorn bound to dynamic $PORT
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 2 --timeout-keep-alive 30 --no-access-log"]

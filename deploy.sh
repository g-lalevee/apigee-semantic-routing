#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Google Cloud Run Deployment Script for Semantic Router Microservice
# ==============================================================================

# Default configurations (override with environment variables if needed)
PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || echo '')}"
REGION="${REGION:-us-central1}"
REPO_NAME="${REPO_NAME:-ai-microservices}"
SERVICE_NAME="${SERVICE_NAME:-semantic-router}"
IMAGE_TAG="${IMAGE_TAG:-v1.0.0}"

if [ -z "$PROJECT_ID" ]; then
    echo "Error: PROJECT_ID is not set and could not be inferred from gcloud config."
    echo "Usage: PROJECT_ID=your-project-id ./deploy.sh"
    exit 1
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "==========================================================="
echo "Project ID    : ${PROJECT_ID}"
echo "Region        : ${REGION}"
echo "Artifact Image: ${IMAGE_URI}"
echo "Service Name  : ${SERVICE_NAME}"
echo "==========================================================="

# 1. Ensure Artifact Registry repository exists
echo "[1/3] Checking/Creating Artifact Registry repository..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
    echo "Creating repository '${REPO_NAME}' in '${REGION}'..."
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${REGION}" \
        --description="Docker repository for AI routing microservices" \
        --project="${PROJECT_ID}"
else
    echo "Repository '${REPO_NAME}' already exists."
fi

# 2. Build and push image using Cloud Build
echo "[2/3] Building container image via Google Cloud Build..."
gcloud builds submit image \
    --tag "${IMAGE_URI}" \
    --project="${PROJECT_ID}"

# 3. Deploy service to Cloud Run
echo "[3/3] Deploying service to Google Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image="${IMAGE_URI}" \
    --region="${REGION}" \
    --platform=managed \
    --project="${PROJECT_ID}" \
    --cpu=2 \
    --memory=2Gi \
    --min-instances=1 \
    --max-instances=10 \
    --concurrency=80 \
    --cpu-boost \
    --timeout=15s \
    --ingress=internal \
    --no-allow-unauthenticated

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --project="${PROJECT_ID}" --format='value(status.url)')
echo "==========================================================="
echo "Deployment successful!"
echo "Service URL: ${SERVICE_URL}"
echo "==========================================================="

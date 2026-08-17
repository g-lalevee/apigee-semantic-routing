# Semantic Router Microservice for Google Cloud Run & Apigee

Production-ready, low-latency semantic router microservice built with **FastAPI** and [Aurelio Labs Semantic Router](https://github.com/aurelio-labs/semantic-router) designed for enterprise API gateway integration (Apigee `ServiceCallout`).

## Key Features

- **Zero Runtime External API Call**: Uses FastEmbed (`BAAI/bge-small-en-v1.5`) backed by ONNX Runtime with baked model weights inside the container image.
- **Sub-10ms Inference**: Vector generation and cosine similarity classification execute locally in CPU memory.
- **Enterprise Security**: Runs under a non-root user (`appuser:appgroup`), handles Cloud Run's dynamic `$PORT`, and supports IAM Google ID Token authentication.
- **Production Pre-Warming**: FastAPI lifespan handler pre-loads and warms up model weights to eliminate cold-start latency spikes.

---

## Repository Structure

```text
.
├── Dockerfile                  # Container definition with baked model weights
├── README.md                   # Documentation and usage guide
├── deploy.sh                   # Automated GCP Cloud Run deployment script
├── main.py                     # FastAPI application & Semantic Router definitions
├── preload_models.py           # Build-time model downloader
├── requirements.txt            # Python dependencies
├── apigee/
│   ├── SC-SemanticRouter.xml       # Apigee ServiceCallout policy
│   └── EV-ExtractRouteDecision.xml  # Apigee ExtractVariables policy
├── .dockerignore
└── .gitignore
```

---

## API Specification

### 1. Evaluate Route (`POST /v1/route`)

**Request Payload:**
```json
{
  "text": "What is our company's refund policy for enterprise tiers?"
}
```

**Response Payload (200 OK):**
```json
{
  "route": "rag-tier",
  "similarity_score": 0.8524
}
```

### 2. Health Check (`GET /healthz`)

**Response Payload (200 OK):**
```json
{
  "status": "healthy"
}
```

---

## Local Development

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run preload script (downloads model to local cache)
python preload_models.py

# Start development server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Local Docker Testing

```bash
# Build the container (model is baked in during build)
docker build -t semantic-router:local .

# Run container
docker run -p 8080:8080 -e PORT=8080 semantic-router:local

# Test routing endpoint
curl -X POST http://localhost:8080/v1/route \
  -H "Content-Type: application/json" \
  -d '{"text": "Solve this differential equation step by step"}'
```

---

## Deployment to Google Cloud Run

Execute the automated deployment script:

```bash
chmod +x deploy.sh
PROJECT_ID="your-gcp-project-id" REGION="us-central1" ./deploy.sh
```

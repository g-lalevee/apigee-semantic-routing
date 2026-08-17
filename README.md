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
├── README.md                   # Documentation and architecture guide
├── deploy.sh                   # Automated GCP Cloud Run deployment script
├── .gitignore
├── apigee/                     # Apigee API Proxy Policies
│   ├── SC-SemanticRouter.xml       # ServiceCallout policy (with Google ID Token auth)
│   └── EV-ExtractRouteDecision.xml  # ExtractVariables policy
└── image/                      # Containerized Microservice Code
    ├── Dockerfile                  # Production container definition (baked model weights)
    ├── main.py                     # FastAPI application & Semantic Router logic
    ├── preload_models.py           # Build-time model downloader
    ├── requirements.txt            # Microservice Python dependencies
    ├── requirements-dev.txt        # Development/Test dependencies
    ├── pytest.ini                  # Pytest configuration
    ├── .dockerignore               # Docker ignore rules
    └── tests/                      # Automated test suite
        ├── conftest.py
        └── test_main.py
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

## Deployment to Google Cloud Run

Execute the automated deployment script:

```bash
chmod +x deploy.sh
PROJECT_ID="your-gcp-project-id" REGION="us-central1" ./deploy.sh
```

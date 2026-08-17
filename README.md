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

The repository includes an automated deployment script [`deploy.sh`](file:///Users/lalevee/Documents/devs/semantic-router-cloudrun/deploy.sh) that builds the container image in Google Cloud Build and deploys it to Google Cloud Run with production resource allocations and security flags.

### 1. Prerequisites Before Running `deploy.sh`

1. **Google Cloud SDK (`gcloud`)**: Authenticated with your GCP account.
   ```bash
   gcloud auth login
   ```
2. **Enable Required Google Cloud APIs**:
   Ensure the following APIs are enabled in your target GCP project:
   ```bash
   gcloud services enable \
       artifactregistry.googleapis.com \
       cloudbuild.googleapis.com \
       run.googleapis.com \
       --project="YOUR_PROJECT_ID"
   ```

---

### 2. Configurable Variables in `deploy.sh`

`deploy.sh` contains default values that can be updated directly in the script or overridden dynamically at runtime using environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PROJECT_ID` | Active `gcloud` project | Google Cloud Project ID where services will be deployed. |
| `REGION` | `us-central1` | GCP region for both Artifact Registry and Cloud Run (e.g. `europe-west1`, `us-central1`). |
| `REPO_NAME` | `ai-microservices` | Artifact Registry Docker repository name (created automatically if missing). |
| `SERVICE_NAME` | `semantic-router` | Name of the Cloud Run microservice. |
| `IMAGE_TAG` | `v1.0.0` | Semantic version tag for the built container image. |

---

### 3. How to Run `deploy.sh`

Make the script executable (if not already done) and execute with your desired configuration:

```bash
chmod +x deploy.sh

# Example 1: Run with explicit environment variables (Recommended)
PROJECT_ID="bap-emea-apigee-5" \
REGION="europe-west1" \
REPO_NAME="semantic-router-repo" \
IMAGE_TAG="v1.0.3" \
./deploy.sh

# Example 2: Run using active gcloud config defaults
./deploy.sh
```

---

### 4. Post-Deployment Steps

#### A. Grant Apigee Invoker Permissions
To allow your Apigee API proxy to call the authenticated Cloud Run service, grant `roles/run.invoker` to your Apigee service account:

```bash
gcloud run services add-iam-policy-binding semantic-router \
    --region="europe-west1" \
    --project="bap-emea-apigee-5" \
    --member="serviceAccount:YOUR_APIGEE_SA@bap-emea-apigee-5.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

#### B. Update Apigee ServiceCallout Policy
Copy the output **Service URL** from `deploy.sh` and update [`apigee/SC-SemanticRouter.xml`](file:///Users/lalevee/Documents/devs/semantic-router-cloudrun/apigee/SC-SemanticRouter.xml):

```xml
<HTTPTargetConnection>
    <Authentication>
        <GoogleIDToken>
            <Audience>https://semantic-router-rafyj6qfzq-ew.a.run.app</Audience>
        </GoogleIDToken>
    </Authentication>
    <URL>https://semantic-router-rafyj6qfzq-ew.a.run.app</URL>
</HTTPTargetConnection>
```

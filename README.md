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
    └── .dockerignore               # Docker ignore rules
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

## How Semantic Routing Works (Route Definitions)

The **Route Definitions** in [`image/main.py`](image/main.py) form the decision-making engine of the microservice. They define the intent categories that incoming user queries are classified into based on **meaning (semantics)** rather than keyword matching.

### 1. Anatomy of a `Route`

Each route is configured with three key parameters:

```python
fast_tier = Route(
    name="fast-tier",          # 1. Identifier returned to Apigee
    utterances=[               # 2. Training example sentences
        "Hello",
        "What is the capital of France?",
        "Translate this sentence to Spanish",
        "Summarize this short email",
    ],
    score_threshold=0.65,      # 3. Minimum cosine similarity confidence score (0.0 - 1.0)
)
```

- **`name`**: The category identifier returned in the JSON response (e.g. `{"route": "fast-tier", "similarity_score": 0.82}`). Apigee uses this value in `<RouteRule>` conditions.
- **`utterances`**: Example sentences defining the semantic "fingerprint" of this route. The local FastEmbed model converts these into 384-dimensional dense vectors. Similar phrases match automatically without exact keyword matching.
- **`score_threshold`**: The confidence threshold. If the highest similarity score for an incoming prompt is below this threshold, the service falls back to `"default"`.

---

### 2. Runtime Evaluation Flow

```
Incoming Request: "Could you please translate this phrase to French?"
                         │
                         ▼
        [FastEmbed converts text to 384d vector in memory]
                         │
                         ▼
         [Calculates Cosine Similarity against all Route Vectors]
                         │
     ┌───────────────────┼───────────────────┐
     ▼                   ▼                   ▼
"fast-tier"       "reasoning-tier"       "rag-tier"
Score: 0.83          Score: 0.21         Score: 0.15
     │
     ▼
Score (0.83) >= Threshold (0.65)? ──▶ YES ──▶ Return {"route": "fast-tier"}
```

---

### 3. Routing Tier Architecture with Apigee

| Route Name | Intended Use Case | Target Backend in Apigee |
| :--- | :--- | :--- |
| **`fast-tier`** | Greetings, short lookups, translations, quick summaries | **Gemini 1.5 Flash** *(low latency & cost)* |
| **`reasoning-tier`** | Complex math, multi-step code architecture, deep logic | **Gemini 1.5 Pro / Thinking** *(high reasoning)* |
| **`rag-tier`** | Internal HR policies, SLAs, enterprise customer records | **Vertex AI Search / RAG Pipeline** |
| **`default`** | Queries not matching any specific route threshold | **Default LLM Target** |

### 4. Customizing Routes

To customize the routing behavior for your enterprise workloads:
1. **Add new routes**: Create additional `Route(...)` objects in [`image/main.py`](image/main.py) (e.g. `sql-generation-tier`, `troubleshooting-tier`).
2. **Tune confidence thresholds**: Adjust `score_threshold` (e.g., raise to `0.75` for stricter matching or lower to `0.55` for broader matching).
3. **Expand utterances**: Add domain-specific phrases to the `utterances` list of any route.

---

### 5. Sample Prompts by Routing Tier

| Route | Sample User Prompt | Semantic Match Reason |
| :--- | :--- | :--- |
| **`fast-tier`** | `"Translate 'Thank you very much' into Spanish."`<br>`"What is the capital city of France?"`<br>`"Summarize this short email into two bullets."` | High-frequency factual lookups, translation, and text utilities. |
| **`reasoning-tier`** | `"Solve this system of differential equations step by step."`<br>`"Write a lock-free concurrent queue in C++."`<br>`"Analyze the EBITDA and cash-flow risk of this acquisition."` | Complex math, multi-step algorithms, deep logic, and architectural analysis. |
| **`rag-tier`** | `"What is our company's refund policy for enterprise tiers?"`<br>`"How do I submit bereavement leave per internal HR guidelines?"`<br>`"Retrieve the latest Q3 engineering roadmap from our wiki."` | Enterprise documentation, HR/legal policies, and internal database records. |
| **`default`** | `"Write a creative fantasy poem about a purple alien planet."`<br>`"What ingredients do I need to make authentic pizza dough?"` | General chitchat or creative tasks not matching a specific threshold. |

#### Testing via Apigee Proxy

```bash
# Apigee Gateway Endpoint
APIGEE_ENDPOINT="https://<YOUR-APIGEE-HOSTNAME>/<BASE-PATH>"

# 1. Test fast-tier
curl -s -X POST "${APIGEE_ENDPOINT}/v1/route" \
  -H "Content-Type: application/json" \
  -d '{"text": "Translate this sentence to Spanish"}'

# 2. Test reasoning-tier
curl -s -X POST "${APIGEE_ENDPOINT}/v1/route" \
  -H "Content-Type: application/json" \
  -d '{"text": "Solve this differential equation and prove the theorem step by step"}'

# 3. Test rag-tier
curl -s -X POST "${APIGEE_ENDPOINT}/v1/route" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is our company internal HR policy on bereavement leave?"}'

# 4. Test default
curl -s -X POST "${APIGEE_ENDPOINT}/v1/route" \
  -H "Content-Type: application/json" \
  -d '{"text": "Write a fictional story about a dragon"}'
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

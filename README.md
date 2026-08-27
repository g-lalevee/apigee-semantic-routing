# Semantic Router Microservice for Google Cloud Run & Apigee

[![PyPI status](https://img.shields.io/pypi/status/ansicolortags.svg)](https://pypi.python.org/pypi/ansicolortags/) 

**This is not an official Google product.**<BR>This implementation is not an official Google product, nor is it part of an official Google product. Support is available on a best-effort basis via GitHub.

***

Low-latency semantic router microservice built with **FastAPI** and [Aurelio Labs Semantic Router](https://github.com/aurelio-labs/semantic-router) designed for enterprise API gateway integration (Apigee `ServiceCallout`).

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
    ├── Dockerfile                  # Container definition (baked model weights)
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

#### Testing Cloud Run Service

```bash
# Set Cloud Run Endpoint & IAM Identity Token
SERVICE_URL="https://<YOUR-CLOUD-RUN-URL>"
TOKEN=$(gcloud auth print-identity-token)

# 1. Test fast-tier
curl -s -X POST "${SERVICE_URL}/v1/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Translate this sentence to Spanish"}'

# 2. Test reasoning-tier
curl -s -X POST "${SERVICE_URL}/v1/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Solve this differential equation and prove the theorem step by step"}'

# 3. Test rag-tier
curl -s -X POST "${SERVICE_URL}/v1/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is our company internal HR policy on bereavement leave?"}'

# 4. Test default
curl -s -X POST "${SERVICE_URL}/v1/route" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"text": "Write a fictional fantasy story about a dragon"}'
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
PROJECT_ID="<YOUR-GCP-PROJECT>" \
REGION="<YOUR-REGION>" \
REPO_NAME="semantic-router-repo" \
IMAGE_TAG="v1.0.3" \
./deploy.sh

# Example 2: Run using active gcloud config defaults
./deploy.sh
```

---

### 4. Cold Starts & Scaling Configuration

> [!NOTE]
> The scale-down limit (minimum instances) of the Cloud Run service is set to zero (to minimize costs when idle): the first call after a period of inactivity will trigger a cold start. Because the container must boot and pre-warm the local semantic router model weights (which takes a few seconds), this first call will take longer and may result in a `504 Gateway Timeout` error if your client or Apigee ServiceCallout timeout is set too low.

To prevent cold starts and ensure sub-10ms response times for all calls, you can configure Cloud Run to keep at least one instance warm:

- **Via the Deployment Script**: Modify the `--min-instances` parameter in [`deploy.sh`](file:///Users/lalevee/Documents/devs/Apigee-semantic-router-cloudrun/deploy.sh). Setting `--min-instances=1` keeps at least one instance warm to eliminate cold-start latencies, while `--min-instances=0` allows the service to scale down to zero to save costs.
- **Via the Google Cloud Console UI**:
  1. Open the **Google Cloud Console** and navigate to **Cloud Run**.
  2. Click on your deployed **`semantic-router`** service.
  3. Click **Edit & Deploy New Revision** at the top.
  4. Scroll down to the **Scaling** section.
  5. Set the **Minimum number of instances** to `1` (to keep an instance warm) or `0` (to enable scale-to-zero).
  6. Click **Deploy**.

---

## Apigee API Proxy Configuration

Follow these steps to create and configure an Apigee API Proxy that uses the two policies provided in the [`apigee/`](apigee/) folder to dynamically classify and route user queries to downstream LLMs:

### Step 1: Create a Reverse Proxy in Apigee
1. In the **Apigee Console**, navigate to **Proxy development > API Proxies > Create**.
2. Select **Reverse proxy (most common)**.
3. Set **Proxy Name** (e.g., `semantic-llm-router`) and **Base Path** (e.g., `/v1/chat`).
4. Set a placeholder Target (e.g. `https://generativelanguage.googleapis.com`).

---

### Step 2: Attach the 2 Policies to Request PreFlow

Import [`apigee/SC-SemanticRouter.xml`](apigee/SC-SemanticRouter.xml) and [`apigee/EV-ExtractRouteDecision.xml`](apigee/EV-ExtractRouteDecision.xml) into your proxy policies directory, and attach them sequentially in the **ProxyEndpoint Request PreFlow**:

```xml
<ProxyEndpoint name="default">
    <PreFlow name="PreFlow">
        <Request>
            <!-- 1. Invoke Cloud Run Semantic Router with user prompt -->
            <Step>
                <Name>SC-SemanticRouter</Name>
            </Step>
            <!-- 2. Extract route name and similarity score into flow variables -->
            <Step>
                <Name>EV-ExtractRouteDecision</Name>
            </Step>
        </Request>
        <Response/>
    </PreFlow>
    ...
</ProxyEndpoint>
```

---

### Step 3: Configure Conditional Route Rules (`default.xml`)

In your ProxyEndpoint configuration (`proxies/default.xml`), define conditional `<RouteRule>` elements that inspect the extracted flow variable `route_name`:

```xml
<ProxyEndpoint name="default">
    ...
    <!-- Dynamic Semantic Routing Rules -->
    <RouteRule name="FastTierRoute">
        <Condition>route_name = "fast-tier"</Condition>
        <TargetEndpoint>Target-Gemini-Flash</TargetEndpoint>
    </RouteRule>

    <RouteRule name="ReasoningTierRoute">
        <Condition>route_name = "reasoning-tier"</Condition>
        <TargetEndpoint>Target-Gemini-Pro</TargetEndpoint>
    </RouteRule>

    <RouteRule name="RAGTierRoute">
        <Condition>route_name = "rag-tier"</Condition>
        <TargetEndpoint>Target-Vertex-Search-RAG</TargetEndpoint>
    </RouteRule>

    <!-- Fallback Route when confidence threshold is not met -->
    <RouteRule name="DefaultRoute">
        <TargetEndpoint>Target-Default-LLM</TargetEndpoint>
    </RouteRule>
</ProxyEndpoint>
```

---

### Step 4: Configure Target Endpoints

Create the corresponding TargetEndpoint definitions under `targets/` in your Apigee proxy bundle:

- `targets/Target-Gemini-Flash.xml`: Configured for low-latency queries (Gemini 1.5 Flash).
- `targets/Target-Gemini-Pro.xml`: Configured for deep analytical logic (Gemini 1.5 Pro / Thinking).
- `targets/Target-Vertex-Search-RAG.xml`: Configured for enterprise internal search & retrieval.
- `targets/Target-Default-LLM.xml`: Configured for general default queries.

---

### 4. Post-Deployment Steps

#### A. Grant Apigee Invoker Permissions
To allow your Apigee API proxy to call the authenticated Cloud Run service, grant `roles/run.invoker` to your Apigee service account:

```bash
gcloud run services add-iam-policy-binding semantic-router \
    --region="<YOUR-REGION>" \
    --project="<YOUR-GCP-PROJECT>" \
    --member="serviceAccount:YOUR_APIGEE_SA@<YOUR-GCP-PROJECT>.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

#### B. Update Apigee ServiceCallout Policy
Copy the output **Service URL** from `deploy.sh` and update [`apigee/SC-SemanticRouter.xml`](file:///Users/lalevee/Documents/devs/semantic-router-cloudrun/apigee/SC-SemanticRouter.xml):

```xml
<HTTPTargetConnection>
    <Authentication>
        <GoogleIDToken>
            <Audience>https://<YOUR-CLOUD-RUN-URL></Audience>
        </GoogleIDToken>
    </Authentication>
    <URL>https://<YOUR-CLOUD-RUN-URL></URL>
</HTTPTargetConnection>
```

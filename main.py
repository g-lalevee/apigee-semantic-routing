import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field
from semantic_router import Route
from semantic_router.encoders import FastEmbedEncoder
from semantic_router.routers import SemanticRouter

# Configure structured logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("semantic-router-service")

# Global reference for router
router: Optional[SemanticRouter] = None

# ---------------------------------------------------------
# 1. Route Definitions
# ---------------------------------------------------------
fast_tier = Route(
    name="fast-tier",
    utterances=[
        "Hello",
        "Hi there",
        "Good morning",
        "What is the capital of France?",
        "Translate this sentence to Spanish",
        "Summarize this short email",
        "What is the current time in Tokyo?",
        "Spell check this sentence",
        "Convert 100 USD to EUR",
        "Give me a quick synonym for fast",
    ],
    score_threshold=0.65,
)

reasoning_tier = Route(
    name="reasoning-tier",
    utterances=[
        "Solve this complex mathematical proof step by step",
        "Write a high-performance concurrent algorithm in Rust",
        "Debug this distributed dead-lock trace across microservices",
        "Analyze the financial risk and EBITDA impact of this corporate acquisition",
        "Formulate a quantitative trading strategy using Monte Carlo simulations",
        "Perform a deep architectural review of this event-driven cloud system",
        "Explain quantum entanglement and quantum teleportation in theoretical physics",
    ],
    score_threshold=0.65,
)

rag_tier = Route(
    name="rag-tier",
    utterances=[
        "What is our enterprise SLA for 99.99% uptime guarantees?",
        "According to our internal HR policy, how do I submit bereavement leave?",
        "Retrieve customer invoice history for enterprise account ACME-90210",
        "What does the internal security standard say about API token rotation?",
        "Look up the internal Q3 engineering roadmap in the company wiki",
        "What are the compliance guidelines for handling EU customer PII in our database?",
    ],
    score_threshold=0.65,
)


# ---------------------------------------------------------
# 2. Application Lifespan (Startup & Warmup)
# ---------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    global router
    logger.info("Initializing local FastEmbed encoder and SemanticRouter...")

    # FastEmbed uses local baked weights without contacting external APIs
    model_name = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-small-en-v1.5")
    cache_dir = os.getenv("FASTEMBED_CACHE_PATH", "/app/model_cache")

    encoder = FastEmbedEncoder(
        name=model_name,
        cache_dir=cache_dir,
    )

    routes = [fast_tier, reasoning_tier, rag_tier]
    router = SemanticRouter(encoder=encoder, routes=routes, auto_sync="local")

    # Perform JIT model warmup to eliminate first-request latency spikes
    logger.info("Warming up embedding model and index...")
    warmup_start = time.perf_counter()
    _ = router("warmup probe text")
    warmup_duration_ms = (time.perf_counter() - warmup_start) * 1000
    logger.info(f"Model warmup complete in {warmup_duration_ms:.2f}ms. Ready to serve.")

    yield

    logger.info("Shutting down semantic router service.")


app = FastAPI(
    title="Apigee Semantic Router Microservice",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------
# 3. Schemas (Pydantic v2)
# ---------------------------------------------------------
class RouteRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=4096,
        description="The user input prompt or query string to route.",
        json_schema_extra={"example": "What is our company's refund policy for enterprise tiers?"},
    )


class RouteResponse(BaseModel):
    route: str = Field(
        ...,
        description="Matched routing tier or fallback default.",
        json_schema_extra={"example": "rag-tier"},
    )
    similarity_score: float = Field(
        ...,
        description="Cosine similarity confidence score (0.0 to 1.0).",
        json_schema_extra={"example": 0.85},
    )


class HealthResponse(BaseModel):
    status: str = "healthy"


# ---------------------------------------------------------
# 4. API Endpoints
# ---------------------------------------------------------
@app.get(
    "/healthz",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness and Readiness Probe",
)
async def healthz():
    if router is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Router is not ready",
        )
    return HealthResponse(status="healthy")


@app.post(
    "/v1/route",
    response_model=RouteResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Semantic Route",
)
async def evaluate_route(request: RouteRequest):
    if router is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Router not initialized",
        )

    start_time = time.perf_counter()

    try:
        choice = router(request.text)

        # Extract route name and score with safe fallback handling
        matched_route = choice.name if (choice and choice.name) else "default"
        similarity_score = (
            float(choice.similarity_score)
            if (choice and choice.similarity_score is not None)
            else 0.0
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.debug(
            f"Evaluated input: '{request.text[:40]}...' -> "
            f"route: '{matched_route}' (score: {similarity_score:.4f}) in {latency_ms:.2f}ms"
        )

        return RouteResponse(
            route=matched_route,
            similarity_score=round(similarity_score, 4),
        )
    except Exception as exc:
        logger.error(f"Routing evaluation error: {str(exc)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error during semantic classification",
        )

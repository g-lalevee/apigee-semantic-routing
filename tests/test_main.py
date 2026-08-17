import time
import pytest
from fastapi.testclient import TestClient


def test_healthcheck(client: TestClient):
    """Verify healthcheck endpoint returns 200 OK and status 'healthy'."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.parametrize(
    "prompt,expected_route",
    [
        ("Good morning! How are you today?", "fast-tier"),
        ("Translate this greeting into Spanish please", "fast-tier"),
        ("What is the capital city of France?", "fast-tier"),
        ("What is the current time in Tokyo?", "fast-tier"),
    ],
)
def test_route_fast_tier(client: TestClient, prompt: str, expected_route: str):
    """Verify quick, general queries match fast-tier."""
    response = client.post("/v1/route", json={"text": prompt})
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == expected_route
    assert data["similarity_score"] >= 0.65


@pytest.mark.parametrize(
    "prompt,expected_route",
    [
        ("Solve this complex mathematical proof step by step", "reasoning-tier"),
        ("Write a high-performance concurrent algorithm in Rust with mutex locks", "reasoning-tier"),
        ("Analyze the financial risk and EBITDA impact of this corporate acquisition", "reasoning-tier"),
    ],
)
def test_route_reasoning_tier(client: TestClient, prompt: str, expected_route: str):
    """Verify deep analytical queries match reasoning-tier."""
    response = client.post("/v1/route", json={"text": prompt})
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == expected_route
    assert data["similarity_score"] >= 0.65


@pytest.mark.parametrize(
    "prompt,expected_route",
    [
        ("What is our enterprise SLA for 99.99% uptime guarantees?", "rag-tier"),
        ("According to our internal HR policy, how do I submit bereavement leave?", "rag-tier"),
        ("Retrieve customer invoice history for enterprise account ACME-90210", "rag-tier"),
    ],
)
def test_route_rag_tier(client: TestClient, prompt: str, expected_route: str):
    """Verify internal enterprise document queries match rag-tier."""
    response = client.post("/v1/route", json={"text": prompt})
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == expected_route
    assert data["similarity_score"] >= 0.65


def test_route_default_fallback(client: TestClient):
    """Verify queries that do not meet the similarity threshold fall back to 'default'."""
    unrelated_text = "qwkjlhasdf 91238491823 kjashdfoiuwe"
    response = client.post("/v1/route", json={"text": unrelated_text})
    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "default"


def test_route_validation_empty_text(client: TestClient):
    """Verify empty string triggers HTTP 422 validation error."""
    response = client.post("/v1/route", json={"text": ""})
    assert response.status_code == 422


def test_route_validation_missing_field(client: TestClient):
    """Verify missing 'text' field triggers HTTP 422 validation error."""
    response = client.post("/v1/route", json={"unrelated_field": "hello"})
    assert response.status_code == 422


def test_route_latency_benchmark(client: TestClient):
    """Verify inference latency is within expected low-latency threshold (< 100ms on CPU)."""
    prompt = "What is the capital of France?"
    start = time.perf_counter()
    response = client.post("/v1/route", json={"text": prompt})
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert response.status_code == 200
    assert elapsed_ms < 100, f"Expected latency < 100ms, got {elapsed_ms:.2f}ms"

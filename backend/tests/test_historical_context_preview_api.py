"""Tests for `POST /decisions/historical-context/preview` - Decision
Similarity + Historical Insight context for a decision that has not been
created yet (REGRET ENGINE 2.0, powers the NewDecisionPage "Relevant from
your past decisions" section).
"""

from fastapi.testclient import TestClient


def test_preview_with_no_history_returns_found_false(client: TestClient) -> None:
    response = client.post(
        "/api/v1/decisions/historical-context/preview",
        json={"title": "First ever decision", "description": "Nothing to compare against yet."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is False


def test_preview_never_persists_a_decision(client: TestClient) -> None:
    before = client.get("/api/v1/decisions").json()["items"]

    client.post(
        "/api/v1/decisions/historical-context/preview",
        json={"title": "Draft decision", "description": "Just typing, not submitted yet."},
    )

    after = client.get("/api/v1/decisions").json()["items"]
    assert len(after) == len(before)


def test_preview_finds_similar_already_created_decision(client: TestClient) -> None:
    client.post(
        "/api/v1/decisions",
        json={
            "title": "Open a cloud kitchen",
            "description": "Considering a Rs 5 lakh investment in a cloud kitchen in Mumbai.",
        },
    )

    response = client.post(
        "/api/v1/decisions/historical-context/preview",
        json={
            "title": "Open a cloud kitchen",
            "description": "Considering a Rs 5 lakh investment in a cloud kitchen in Mumbai.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["found"] is True
    assert body["relevant_decisions_count"] >= 1


def test_preview_requires_valid_decision_create_payload(client: TestClient) -> None:
    response = client.post("/api/v1/decisions/historical-context/preview", json={"title": ""})
    assert response.status_code == 422

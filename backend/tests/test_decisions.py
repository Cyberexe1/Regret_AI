"""Tests for the DynamoDB-backed decision API.

All tests run against a moto-mocked DynamoDB (see `conftest.py`) - no real
AWS account, credentials, or network access is required or used.
"""

from fastapi.testclient import TestClient

VALID_PAYLOAD = {
    "title": "Open a second bakery location",
    "description": "Considering a second storefront in the downtown district.",
    "desired_outcome": "Break even within 12 months",
    "budget": 50000,
    "currency": "USD",
    "timeline": "6 months",
    "location": "Downtown",
    "risk_tolerance": "medium",
    "beliefs": "Foot traffic downtown is high enough to sustain a second store.",
}


def test_create_decision_returns_draft(client: TestClient) -> None:
    response = client.post("/api/v1/decisions", json=VALID_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["title"] == VALID_PAYLOAD["title"]
    assert body["description"] == VALID_PAYLOAD["description"]
    assert body["budget"] == VALID_PAYLOAD["budget"]
    assert body["status"] == "draft"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body
    assert "user_id" not in body


def test_create_decision_with_minimal_payload(client: TestClient) -> None:
    minimal_payload = {
        "title": "Switch to a four-day work week",
        "description": "Evaluating whether a compressed schedule hurts delivery speed.",
    }

    response = client.post("/api/v1/decisions", json=minimal_payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "draft"
    assert body["budget"] is None


def test_create_decision_missing_required_field_returns_422(client: TestClient) -> None:
    response = client.post("/api/v1/decisions", json={"title": "Missing description"})

    assert response.status_code == 422


def test_get_decision_after_create(client: TestClient) -> None:
    create_response = client.post("/api/v1/decisions", json=VALID_PAYLOAD)
    decision_id = create_response.json()["id"]

    get_response = client.get(f"/api/v1/decisions/{decision_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == decision_id


def test_get_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404
    body = response.json()
    # Standardized error envelope (see app.core.errors): "detail" is kept
    # for backward compatibility, "error" carries the machine-readable
    # code + request id for correlating with server-side logs.
    assert body["detail"] == "Decision 00000000-0000-0000-0000-000000000000 not found."
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["message"] == "Decision 00000000-0000-0000-0000-000000000000 not found."
    assert body["error"]["request_id"]


def test_get_decision_with_invalid_id_returns_422(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/not-a-uuid")

    assert response.status_code == 422


def test_list_decisions_includes_created_decision(client: TestClient) -> None:
    create_response = client.post("/api/v1/decisions", json=VALID_PAYLOAD)
    decision_id = create_response.json()["id"]

    list_response = client.get("/api/v1/decisions")

    assert list_response.status_code == 200
    body = list_response.json()
    ids = [decision["id"] for decision in body["items"]]
    assert decision_id in ids


def test_list_decisions_newest_first(client: TestClient) -> None:
    first = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()
    second_payload = {**VALID_PAYLOAD, "title": "A different decision"}
    second = client.post("/api/v1/decisions", json=second_payload).json()

    body = client.get("/api/v1/decisions").json()

    ids = [item["id"] for item in body["items"]]
    assert ids.index(second["id"]) < ids.index(first["id"])


def test_list_decisions_pagination(client: TestClient) -> None:
    for i in range(5):
        payload = {**VALID_PAYLOAD, "title": f"Decision {i}"}
        client.post("/api/v1/decisions", json=payload)

    first_page = client.get("/api/v1/decisions", params={"limit": 2}).json()
    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_page = client.get(
        "/api/v1/decisions", params={"limit": 2, "cursor": first_page["next_cursor"]}
    ).json()
    assert len(second_page["items"]) == 2

    first_ids = {item["id"] for item in first_page["items"]}
    second_ids = {item["id"] for item in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_list_decisions_respects_limit_bounds(client: TestClient) -> None:
    too_high = client.get("/api/v1/decisions", params={"limit": 500})
    too_low = client.get("/api/v1/decisions", params={"limit": 0})

    assert too_high.status_code == 422
    assert too_low.status_code == 422


def test_update_decision(client: TestClient) -> None:
    decision_id = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()["id"]

    response = client.patch(f"/api/v1/decisions/{decision_id}", json={"title": "Renamed decision"})

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed decision"
    assert body["description"] == VALID_PAYLOAD["description"]  # untouched


def test_update_decision_status(client: TestClient) -> None:
    decision_id = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()["id"]

    response = client.patch(f"/api/v1/decisions/{decision_id}", json={"status": "queued"})

    assert response.status_code == 200
    assert response.json()["status"] == "queued"


def test_update_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.patch(
        "/api/v1/decisions/00000000-0000-0000-0000-000000000000", json={"title": "x"}
    )

    assert response.status_code == 404


def test_update_decision_with_stale_expected_updated_at_returns_409(client: TestClient) -> None:
    created = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()
    decision_id = created["id"]

    # Apply one real update so `updated_at` on the stored item changes...
    client.patch(f"/api/v1/decisions/{decision_id}", json={"title": "First update"})

    # ...then attempt a second update guarded by the *original* (now stale)
    # updated_at. This must lose the race.
    response = client.patch(
        f"/api/v1/decisions/{decision_id}",
        json={"title": "Second update", "expected_updated_at": created["updated_at"]},
    )

    assert response.status_code == 409


def test_update_decision_with_fresh_expected_updated_at_succeeds(client: TestClient) -> None:
    created = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()
    decision_id = created["id"]

    response = client.patch(
        f"/api/v1/decisions/{decision_id}",
        json={"title": "Updated safely", "expected_updated_at": created["updated_at"]},
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated safely"


def test_delete_decision(client: TestClient) -> None:
    decision_id = client.post("/api/v1/decisions", json=VALID_PAYLOAD).json()["id"]

    delete_response = client.delete(f"/api/v1/decisions/{decision_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/decisions/{decision_id}")
    assert get_response.status_code == 404


def test_delete_unknown_decision_returns_404(client: TestClient) -> None:
    response = client.delete("/api/v1/decisions/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404

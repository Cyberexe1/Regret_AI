"""Tests for the evidence upload/retrieval/deletion API.

Runs against a moto-mocked DynamoDB and a pytest temp-directory storage
backend (see `conftest.py`) - no real AWS account or network access.
"""

import io

from fastapi.testclient import TestClient

DECISION_PAYLOAD = {
    "title": "Open a second bakery location",
    "description": "Considering a second storefront in the downtown district.",
}


def _create_decision(client: TestClient) -> str:
    response = client.post("/api/v1/decisions", json=DECISION_PAYLOAD)
    assert response.status_code == 201
    return response.json()["id"]


def _make_txt_upload(text: str = "Foot traffic downtown rose 12% this quarter.") -> dict:
    return {"file": ("notes.txt", io.BytesIO(text.encode("utf-8")), "text/plain")}


def _make_minimal_pdf_bytes() -> bytes:
    """A tiny, syntactically valid single-page PDF for upload tests.

    Built with pypdf's own writer rather than a fixture file, so the test
    suite has no binary assets to track and the PDF is guaranteed to be
    structurally valid (correct xref table/offsets).
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def test_upload_txt_evidence(client: TestClient) -> None:
    decision_id = _create_decision(client)

    response = client.post(
        f"/api/v1/decisions/{decision_id}/evidence", files=_make_txt_upload()
    )

    assert response.status_code == 201
    body = response.json()
    assert body["decision_id"] == decision_id
    assert body["file_type"] == "txt"
    assert body["filename"] == "notes.txt"
    assert "Foot traffic" in body["content_reference"]
    assert body["content_truncated"] is False
    assert body["page_count"] is None
    assert "id" in body


def test_upload_pdf_evidence(client: TestClient) -> None:
    decision_id = _create_decision(client)
    files = {"file": ("report.pdf", io.BytesIO(_make_minimal_pdf_bytes()), "application/pdf")}

    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["file_type"] == "pdf"
    assert body["page_count"] == 1


def test_upload_invalid_extension_is_rejected(client: TestClient) -> None:
    decision_id = _create_decision(client)
    files = {
        "file": ("script.exe", io.BytesIO(b"not really an executable"), "application/x-msdownload")
    }

    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=files)

    assert response.status_code == 415


def test_upload_mislabeled_file_is_rejected(client: TestClient) -> None:
    """A .pdf extension on content that isn't actually PDF bytes must fail.

    This is the content-sniffing check: the client-claimed extension alone
    is never trusted.
    """
    decision_id = _create_decision(client)
    files = {"file": ("fake.pdf", io.BytesIO(b"this is just plain text"), "application/pdf")}

    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=files)

    assert response.status_code == 415


def test_upload_oversized_file_is_rejected(client: TestClient, monkeypatch) -> None:
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("MAX_UPLOAD_SIZE_BYTES", "10")
    config.get_settings.cache_clear()

    decision_id = _create_decision(client)
    oversized_upload = _make_txt_upload("this text is way over ten bytes")
    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=oversized_upload)

    config.get_settings.cache_clear()
    assert response.status_code == 413


def test_upload_empty_file_is_rejected(client: TestClient) -> None:
    decision_id = _create_decision(client)
    files = {"file": ("empty.txt", io.BytesIO(b""), "text/plain")}

    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=files)

    assert response.status_code == 415


def test_upload_to_missing_decision_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/decisions/00000000-0000-0000-0000-000000000000/evidence",
        files=_make_txt_upload(),
    )

    assert response.status_code == 404


def test_list_evidence_for_decision(client: TestClient) -> None:
    decision_id = _create_decision(client)
    client.post(f"/api/v1/decisions/{decision_id}/evidence", files=_make_txt_upload())

    response = client.get(f"/api/v1/decisions/{decision_id}/evidence")

    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["decision_id"] == decision_id


def test_list_evidence_for_missing_decision_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/00000000-0000-0000-0000-000000000000/evidence")

    assert response.status_code == 404


def test_get_evidence_by_id(client: TestClient) -> None:
    decision_id = _create_decision(client)
    upload = client.post(
        f"/api/v1/decisions/{decision_id}/evidence", files=_make_txt_upload()
    ).json()

    response = client.get(f"/api/v1/evidence/{upload['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == upload["id"]


def test_get_unknown_evidence_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/evidence/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_delete_evidence(client: TestClient) -> None:
    decision_id = _create_decision(client)
    upload = client.post(
        f"/api/v1/decisions/{decision_id}/evidence", files=_make_txt_upload()
    ).json()

    delete_response = client.delete(f"/api/v1/evidence/{upload['id']}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/evidence/{upload['id']}")
    assert get_response.status_code == 404


def test_delete_unknown_evidence_returns_404(client: TestClient) -> None:
    response = client.delete("/api/v1/evidence/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 404


def test_long_document_content_is_truncated(client: TestClient) -> None:
    decision_id = _create_decision(client)
    long_text = "word " * 10_000  # well over the 20,000-char bound
    files = {"file": ("long.txt", io.BytesIO(long_text.encode("utf-8")), "text/plain")}

    response = client.post(f"/api/v1/decisions/{decision_id}/evidence", files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["content_truncated"] is True
    assert len(body["content_reference"]) <= 20_000

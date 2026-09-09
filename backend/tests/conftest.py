"""Shared pytest fixtures.

Every test that touches the database goes through the `dynamodb_table`
fixture, which spins up a moto-mocked DynamoDB, creates the table fresh,
and clears the module-level resource/table cache on the way in and out.
No test in this suite talks to a real AWS account.

Tests that upload evidence go through the `client` fixture, which also
redirects local file storage to a pytest-managed temp directory instead of
the real `./data/evidence` used by the running application.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.main import app
from app.repositories.dynamodb import create_table_if_not_exists, reset_dynamodb_cache
from app.services.storage import LocalStorageBackend, get_storage_backend


@pytest.fixture
def dynamodb_table() -> Iterator[None]:
    with mock_aws():
        reset_dynamodb_cache()
        create_table_if_not_exists()
        yield
    reset_dynamodb_cache()


@pytest.fixture
def client(dynamodb_table: None, tmp_path: Path) -> Iterator[TestClient]:
    app.dependency_overrides[get_storage_backend] = lambda: LocalStorageBackend(root=tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_storage_backend, None)

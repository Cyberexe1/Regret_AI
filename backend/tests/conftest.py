"""Shared pytest fixtures.

Every test that touches the database goes through the `dynamodb_table`
fixture, which spins up a moto-mocked DynamoDB, creates the table fresh,
and clears the module-level resource/table cache on the way in and out.
No test in this suite talks to a real AWS account.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from app.main import app
from app.repositories.dynamodb import create_table_if_not_exists, reset_dynamodb_cache


@pytest.fixture
def dynamodb_table() -> Iterator[None]:
    with mock_aws():
        reset_dynamodb_cache()
        create_table_if_not_exists()
        yield
    reset_dynamodb_cache()


@pytest.fixture
def client(dynamodb_table: None) -> TestClient:
    return TestClient(app)

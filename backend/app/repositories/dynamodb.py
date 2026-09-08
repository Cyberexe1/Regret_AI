"""Low-level DynamoDB access.

Every other repository in this package goes through `DynamoDBGateway`
instead of importing boto3 directly. That keeps three things centralized:

- how the boto3 resource/table is constructed and cached (one per process,
  not one per request)
- how Python floats are converted to/from DynamoDB's `Decimal` requirement
- how botocore failures are translated into the application's own error
  types, so nothing about AWS internals (error codes, request ids) ever
  reaches an API response

No FastAPI route or service should import boto3/botocore directly.
"""

from decimal import Decimal
from functools import lru_cache
from typing import Any

import boto3
from boto3.dynamodb.conditions import ConditionBase
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import get_settings
from app.core.errors import ConflictError, RepositoryError
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache
def get_dynamodb_resource() -> Any:
    """Return a process-wide boto3 DynamoDB resource.

    Credentials are never constructed here - boto3 resolves them through
    its standard provider chain (environment variables, shared credentials
    file, an assumed role, or an instance profile). `aws_endpoint_url` is
    only used to redirect requests to a local DynamoDB-compatible endpoint
    for development; it is unset (None) for real AWS usage.
    """
    settings = get_settings()
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.aws_endpoint_url:
        kwargs["endpoint_url"] = settings.aws_endpoint_url
    return boto3.resource("dynamodb", **kwargs)


@lru_cache
def get_table() -> Any:
    """Return the single application table, cached for the process lifetime."""
    settings = get_settings()
    return get_dynamodb_resource().Table(settings.dynamodb_table_name)


def reset_dynamodb_cache() -> None:
    """Clear cached resource/table handles.

    Used by tests so each moto-mocked test gets a fresh client instead of
    reusing one bound to a previous (now-torn-down) mock session.
    """
    get_dynamodb_resource.cache_clear()
    get_table.cache_clear()


def to_dynamo_value(value: Any) -> Any:
    """Recursively convert Python-native numeric types to `Decimal`.

    DynamoDB's boto3 resource API rejects native `float` values outright, so
    every write path funnels through this first.
    """
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: to_dynamo_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [to_dynamo_value(item) for item in value]
    return value


def from_dynamo_value(value: Any) -> Any:
    """Recursively convert `Decimal` values back to `int`/`float` for API use."""
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    if isinstance(value, dict):
        return {key: from_dynamo_value(val) for key, val in value.items()}
    if isinstance(value, list):
        return [from_dynamo_value(item) for item in value]
    return value


class DynamoDBGateway:
    """Thin wrapper around a single DynamoDB table.

    Translates botocore exceptions into application errors and handles the
    Decimal<->float conversion boto3's resource API requires, so repository
    subclasses can work with plain Python dicts.
    """

    def __init__(self, table: Any | None = None) -> None:
        self._table = table if table is not None else get_table()

    def put_item(self, item: dict[str, Any], condition: ConditionBase | None = None) -> None:
        kwargs: dict[str, Any] = {"Item": to_dynamo_value(item)}
        if condition is not None:
            kwargs["ConditionExpression"] = condition
        self._run(self._table.put_item, **kwargs)

    def get_item(self, key: dict[str, Any]) -> dict[str, Any] | None:
        response = self._run(self._table.get_item, Key=key)
        item = response.get("Item")
        return from_dynamo_value(item) if item is not None else None

    def delete_item(self, key: dict[str, Any], condition: ConditionBase | None = None) -> None:
        kwargs: dict[str, Any] = {"Key": key}
        if condition is not None:
            kwargs["ConditionExpression"] = condition
        self._run(self._table.delete_item, **kwargs)

    def update_item(
        self,
        key: dict[str, Any],
        update_expression: str,
        expression_attribute_values: dict[str, Any],
        expression_attribute_names: dict[str, str] | None = None,
        condition: ConditionBase | None = None,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "Key": key,
            "UpdateExpression": update_expression,
            "ExpressionAttributeValues": to_dynamo_value(expression_attribute_values),
            "ReturnValues": "ALL_NEW",
        }
        if expression_attribute_names:
            kwargs["ExpressionAttributeNames"] = expression_attribute_names
        if condition is not None:
            kwargs["ConditionExpression"] = condition
        response = self._run(self._table.update_item, **kwargs)
        return from_dynamo_value(response.get("Attributes", {}))

    def query(
        self,
        key_condition: ConditionBase,
        index_name: str | None = None,
        limit: int | None = None,
        exclusive_start_key: dict[str, Any] | None = None,
        scan_index_forward: bool = True,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        kwargs: dict[str, Any] = {
            "KeyConditionExpression": key_condition,
            "ScanIndexForward": scan_index_forward,
        }
        if index_name:
            kwargs["IndexName"] = index_name
        if limit:
            kwargs["Limit"] = limit
        if exclusive_start_key:
            kwargs["ExclusiveStartKey"] = exclusive_start_key

        response = self._run(self._table.query, **kwargs)
        items = [from_dynamo_value(item) for item in response.get("Items", [])]
        return items, response.get("LastEvaluatedKey")

    def _run(self, operation: Any, **kwargs: Any) -> Any:
        try:
            return operation(**kwargs)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ConditionalCheckFailedException":
                logger.warning("DynamoDB conditional check failed: %s", operation.__name__)
                raise ConflictError() from exc
            logger.error(
                "DynamoDB request failed: op=%s code=%s", operation.__name__, error_code
            )
            raise RepositoryError() from exc
        except BotoCoreError as exc:
            logger.error("DynamoDB client error: op=%s type=%s", operation.__name__, type(exc).__name__)
            raise RepositoryError() from exc


def create_table_if_not_exists() -> None:
    """Create the single application table if it doesn't already exist.

    Intended for local development bootstrap (see `scripts/create_table.py`)
    against either real AWS or a local DynamoDB-compatible endpoint. Not
    called automatically at application startup - table provisioning in a
    real AWS account should be deliberate (or managed via infrastructure
    tooling later), not an implicit side effect of starting the API.
    """
    settings = get_settings()
    resource = get_dynamodb_resource()
    existing_tables = {table.name for table in resource.tables.all()}

    if settings.dynamodb_table_name in existing_tables:
        logger.info("Table %s already exists, skipping creation.", settings.dynamodb_table_name)
        return

    table = resource.create_table(
        TableName=settings.dynamodb_table_name,
        KeySchema=[
            {"AttributeName": "PK", "KeyType": "HASH"},
            {"AttributeName": "SK", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "PK", "AttributeType": "S"},
            {"AttributeName": "SK", "AttributeType": "S"},
            {"AttributeName": "GSI1PK", "AttributeType": "S"},
            {"AttributeName": "GSI1SK", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "GSI1",
                "KeySchema": [
                    {"AttributeName": "GSI1PK", "KeyType": "HASH"},
                    {"AttributeName": "GSI1SK", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )
    table.wait_until_exists()
    logger.info("Created table %s", settings.dynamodb_table_name)

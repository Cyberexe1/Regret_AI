"""One-off local dev helper: create the DynamoDB table if it's missing.

Usage:

    python scripts/create_table.py

Works against either:
  - a local DynamoDB-compatible endpoint, if AWS_ENDPOINT_URL is set in
    your environment/.env (e.g. DynamoDB Local at http://localhost:8000)
  - real AWS DynamoDB in AWS_REGION, if AWS_ENDPOINT_URL is unset

This is never called automatically by the application. Provisioning a
table in a real AWS account should be a deliberate, explicit action.
"""

import sys
from pathlib import Path

# Allow running as `python scripts/create_table.py` from the backend/ root
# without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.repositories.dynamodb import create_table_if_not_exists  # noqa: E402


def main() -> None:
    create_table_if_not_exists()


if __name__ == "__main__":
    main()

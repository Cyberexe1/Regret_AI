# REGRET ENGINE backend - production container image.
#
# All configuration comes from environment variables at runtime (see
# .env.example / README.md "Environment setup") - nothing here bakes in
# AWS credentials, a Bedrock model id, or any other secret. AWS credentials
# are resolved by boto3's standard provider chain, exactly as documented in
# README.md - typically an IAM role (ECS task role / EC2 instance profile /
# Lambda execution role) when running in AWS.

FROM python:3.12-slim AS base

# Prevents Python from writing .pyc files and buffering stdout/stderr -
# both make container logs behave predictably.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only what's needed to run the API - test/lint tooling
# (pytest/ruff/moto) is still listed in requirements.txt for local dev
# parity, but is harmless (small, pure-Python) to include here too rather
# than maintaining a second requirements file; nothing in this image
# executes tests.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts ./scripts

# Run as a non-root user - defense in depth in case a dependency is ever
# compromised, the process still can't write outside its own directories
# or bind privileged ports.
RUN addgroup --system regret && adduser --system --ingroup regret regret \
    && mkdir -p /app/data/evidence \
    && chown -R regret:regret /app
USER regret

EXPOSE 8000

# A lightweight liveness probe against the app's own health endpoint - see
# app/api/routes/health.py. Does not check external dependencies
# (DynamoDB/Bedrock/research) - use GET /api/v1/ready for that.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# REGRET ENGINE — Backend

## 1. Project purpose

REGRET ENGINE is an AI decision-intelligence product. A user describes a
decision they're facing, and the system is meant to eventually:

1. Understand the decision
2. Identify assumptions
3. Discover blindspots
4. Collect evidence
5. Adversarially stress-test the decision
6. Simulate failure/regret scenarios
7. Identify breaking thresholds
8. Recommend the cheapest validation experiment
9. Allow re-evaluation as new evidence comes in

This directory is the backend API for that product. **This is Step 1**: a
clean FastAPI foundation with a health check and a decision intake endpoint.
No AI, no database, no cloud infrastructure yet — see [Current
limitations](#8-current-limitations) below.

## 2. Requirements

- Python 3.12 or newer
- pip

## 3. Installation

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 4. Environment setup

Copy the example environment file and adjust as needed:

```powershell
Copy-Item .env.example .env
```

| Variable                | Default                                             | Description                                   |
| ------------------------ | ---------------------------------------------------- | ---------------------------------------------- |
| `APP_NAME`               | `REGRET ENGINE`                                      | Displayed in API docs/OpenAPI.                 |
| `APP_ENV`                | `development`                                        | `development` / `production`.                  |
| `DEBUG`                  | `true`                                                | Enables verbose logging.                       |
| `API_V1_PREFIX`          | `/api/v1`                                            | Prefix for all versioned routes.               |
| `CORS_ALLOWED_ORIGINS`   | `http://localhost:5173,http://127.0.0.1:5173`        | Comma-separated list of allowed frontend origins. Never set to `*` in production. |
| `LOG_LEVEL`              | `INFO`                                               | Root logger level.                             |

No secrets are required for this step. Nothing sensitive should ever be
committed to `.env` — only `.env.example` is tracked in git.

## 5. Running locally

```powershell
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs
at `http://127.0.0.1:8000/docs`.

## 6. Running tests

```powershell
pytest
```

Tests run entirely offline against an in-memory store — no AWS credentials,
database, or network access required.

## 7. API endpoints

| Method | Path                          | Description                                    |
| ------ | ----------------------------- | ----------------------------------------------- |
| GET    | `/api/v1/health`              | Liveness check.                                 |
| POST   | `/api/v1/decisions`           | Submit a new decision (stored as `draft`).      |
| GET    | `/api/v1/decisions`           | List decisions submitted this process run.      |
| GET    | `/api/v1/decisions/{id}`      | Fetch a single decision by id. `404` if unknown. |

### Decision status values

`draft`, `queued`, `analyzing`, `completed`, `needs_validation`, `archived`.

Only `draft` is reachable today — the rest are reserved for the analysis
pipeline built in later steps.

## 8. Current limitations

- **No AI agents.** Decisions are stored as-is; nothing analyzes them.
- **No Strands Agents SDK or Amazon Bedrock integration.**
- **No database.** Storage is in-memory (`app/services/decision_repository.py`)
  and is lost on every restart. It is intentionally isolated behind a small
  repository interface so it can be swapped for PostgreSQL without touching
  route handlers or business logic.
- **No auth.** Every endpoint is currently open; access control is not in
  scope for this step.
- **No AWS deployment.** This runs locally only for now.

## 9. Planned architecture

Roughly, in upcoming steps:

- Replace `DecisionRepository`'s in-memory dict with a PostgreSQL-backed
  implementation behind the same interface.
- Introduce a decision analysis pipeline (assumptions → blindspots →
  evidence → stress test → regret simulation → thresholds → experiment
  recommendation), most likely orchestrated with Strands Agents on top of
  Amazon Bedrock models.
- Move decision status transitions (`draft` → `queued` → `analyzing` → ...)
  into that pipeline as real, observable state changes.
- Add authentication/authorization once there's a real user model.
- Add deployment infrastructure (containerization, AWS hosting) once the
  service is feature-complete enough to deploy.

None of the above is implemented yet — this README will be updated as each
step lands.

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

This directory is the backend API for that product.

- **Step 1** (done): a clean FastAPI foundation with a health check and a
  decision intake endpoint, backed by temporary in-memory storage.
- **Step 2** (done): the in-memory store is replaced with a real
  **Amazon DynamoDB** persistence layer, and the decision API is completed
  (list with pagination, update, delete).
- **Step 3** (done): a document/evidence ingestion layer - uploading
  PDF/DOCX/TXT files as evidence for a decision, extracting their text, and
  storing the file itself through a storage abstraction (local disk today,
  Amazon S3 later).
- **Step 4** (done): the foundation for the AI agent pipeline - a real
  [Strands Agents SDK](https://strandsagents.com/) agent (the **Decision
  Analyzer**) running on **Amazon Bedrock**, orchestrated behind a new
  `/analyze` endpoint.
- **Steps 5-9** (done): the remaining core pipeline agents - Assumption
  Hunter, Blindspot Hunter, Evidence Agent, Devil's Advocate, Regret
  Simulator, Threshold Engine, and Experiment Planner - each added as a
  sequential stage of the same `/analyze` orchestration.
- **Step 10** (done): the experiment result + re-evaluation loop -
  submitting an observed experiment result deterministically re-evaluates
  the target threshold, related assumptions, and related regret scenarios.
- **Step 11** (done): optional external research (Research Agent) with
  strict source grounding, budget limits, and prompt-injection defense -
  entirely separate from user-uploaded evidence.
- **Step 12** (this step): production hardening and AWS-integration
  readiness - request ids, structured logging, standardized error
  responses, analysis idempotency and a status-polling endpoint,
  production configuration validation, concurrency protection, Docker
  packaging, and AWS setup/IAM documentation. No new agents and no product
  behavior changes - see [Current limitations](#14-current-limitations)
  below for what's still out of scope.

## 2. Requirements

- Python 3.12 or newer
- pip
- Either an AWS account with DynamoDB access, **or** a local
  DynamoDB-compatible endpoint for development (see
  [DynamoDB architecture](#10-dynamodb-architecture) below) — a local endpoint
  is not required if you'd rather point straight at AWS.
- An AWS account with **Amazon Bedrock** access (and model access enabled
  for the configured `BEDROCK_MODEL_ID`) to actually call
  `/analyze` against a real model. The rest of the API works without this;
  see [Testing](#6-running-tests) for how the test suite avoids needing it.

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

| Variable                | Default                                      | Description                                                                        |
| ------------------------ | ---------------------------------------------- | ------------------------------------------------------------------------------------ |
| `APP_NAME`               | `REGRET ENGINE`                                | Displayed in API docs/OpenAPI.                                                      |
| `APP_ENV`                | `development`                                  | `development` / `production`.                                                       |
| `DEBUG`                  | `true`                                          | Enables verbose logging.                                                             |
| `API_V1_PREFIX`          | `/api/v1`                                      | Prefix for all versioned routes.                                                     |
| `CORS_ALLOWED_ORIGINS`   | `http://localhost:5173,http://127.0.0.1:5173`  | Comma-separated list of allowed frontend origins. Never set to `*` in production.    |
| `LOG_LEVEL`              | `INFO`                                          | Root logger level.                                                                   |
| `AWS_REGION`             | `ap-south-1`                                    | Region for DynamoDB requests.                                                        |
| `DYNAMODB_TABLE_NAME`    | `regret-engine`                                 | Single application table name.                                                      |
| `AWS_ENDPOINT_URL`       | *(unset)*                                       | Only set for local development against a DynamoDB-compatible endpoint. Leave unset for real AWS DynamoDB. |
| `DEFAULT_USER_ID`        | `local-dev-user`                                | Placeholder identity used until real authentication exists. See [Current limitations](#14-current-limitations). |
| `STORAGE_BACKEND`        | `local`                                         | Evidence file storage backend. Only `local` is implemented; `s3` is reserved for later. |
| `LOCAL_STORAGE_DIR`      | `./data/evidence`                               | Where evidence files are written when using the `local` backend. Requires no AWS credentials. |
| `MAX_UPLOAD_SIZE_BYTES`  | `10485760` (10 MB)                              | Maximum accepted evidence upload size.                                              |
| `ALLOWED_EVIDENCE_EXTENSIONS` | `.pdf,.docx,.txt`                          | Comma-separated allow-list of accepted upload extensions.                           |
| `BEDROCK_MODEL_ID`       | `global.anthropic.claude-sonnet-4-6`            | Bedrock model id the Decision Analyzer uses. Override per account/region if needed. |
| `BEDROCK_INVOKE_TIMEOUT_SECONDS` | `60`                                     | Wall-clock budget for one agent model call before it's treated as a failure.        |
| `S3_BUCKET_NAME`         | *(unset)*                                       | Reserved for the future S3-backed `StorageBackend`. Required in production only if/when `STORAGE_BACKEND=s3`. |
| `RESEARCH_PROVIDER`      | `none`                                          | `none` disables external research entirely; `http` enables the built-in DuckDuckGo HTML-search provider (no API key). |
| `RESEARCH_API_KEY`       | *(unset)*                                       | Only needed by a future provider that requires one. Never commit a real key.        |
| `RESEARCH_MAX_QUERIES` / `RESEARCH_MAX_RESULTS_PER_QUERY` / `RESEARCH_MAX_TOTAL_SOURCES` | `3` / `5` / `10` | Bounds one analysis run's total research fan-out. |
| `RESEARCH_TIMEOUT_SECONDS` / `RESEARCH_MAX_RETRIES` / `RESEARCH_MAX_SNIPPET_CHARS` | `15` / `2` / `1000` | Per-query timeout, bounded retry count, and max untrusted snippet length passed to a model. |
| `ANALYSIS_MAX_DURATION_SECONDS` | `600`                                    | Expected wall-clock budget for one full analysis run (all ~9 sequential stages).     |
| `ANALYSIS_LOCK_GRACE_SECONDS`   | `120`                                    | Extra grace period before a `running` run stuck past the duration above is treated as abandoned (e.g. a crashed process) rather than active, unblocking `/analyze` idempotency for that decision. |
| `MAX_CONCURRENT_ANALYSES`| `5`                                              | Process-wide cap on how many analysis pipelines run at once (each makes several sequential Bedrock calls). Not a distributed rate limiter. |

**No AWS access keys, secret keys, session tokens, or model credentials are
ever set here or anywhere in source.** boto3 (and the Strands Agents SDK's
`BedrockModel`, which uses boto3 internally) resolves credentials through
the standard provider chain — environment variables, `~/.aws/credentials`,
an assumed role, or an EC2/ECS/Lambda instance profile. Only `.env.example`
is tracked in git; your real `.env` never should be.

## 5. Running locally

```powershell
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://127.0.0.1:8000`, with interactive docs
at `http://127.0.0.1:8000/docs`.

The table must exist before the API can serve decision requests — see
[DynamoDB architecture](#10-dynamodb-architecture) for how to create it,
whether you're using real AWS or a local endpoint.

## 6. Running tests

```powershell
pytest
```

Every test runs against [moto](https://github.com/getmoto/moto)'s in-process
DynamoDB mock (`tests/conftest.py`). No real AWS account, credentials, table,
or network access is required or used. The mocked table is created fresh at
the start of every test that needs one and torn down at the end.

Analysis tests (`tests/test_analysis.py`) additionally patch
`app.agents.decision_analyzer.run_decision_analyzer` at its call site inside
the orchestrator, so no test ever makes a real call to Amazon Bedrock either.

## 7. API endpoints

| Method | Path                          | Description                                                                    |
| ------ | ------------------------------ | -------------------------------------------------------------------------------- |
| GET    | `/api/v1/health`               | Liveness check.                                                                  |
| POST   | `/api/v1/decisions`            | Create a new decision (stored as `draft`).                                      |
| GET    | `/api/v1/decisions`            | List the current user's decisions, newest first. Supports `limit` and `cursor`. |
| GET    | `/api/v1/decisions/{id}`       | Fetch a single decision by id. `404` if unknown or not owned by the caller.     |
| PATCH  | `/api/v1/decisions/{id}`       | Partially update a decision. Optionally guarded by `expected_updated_at`.        |
| DELETE | `/api/v1/decisions/{id}`       | Delete a decision. Returns `204`.                                                |
| POST   | `/api/v1/decisions/{id}/evidence` | Upload a PDF/DOCX/TXT file as evidence for a decision.                       |
| GET    | `/api/v1/decisions/{id}/evidence` | List evidence metadata for a decision.                                       |
| GET    | `/api/v1/evidence/{evidence_id}`  | Fetch a single piece of evidence by id.                                      |
| DELETE | `/api/v1/evidence/{evidence_id}`  | Delete a piece of evidence and its underlying stored file. Returns `204`.    |
| POST   | `/api/v1/decisions/{id}/analyze`  | Run the full analysis pipeline for a decision. Idempotent - see [Agent foundation](#9-agent-foundation-decision-analyzer). |
| GET    | `/api/v1/decisions/{id}/analysis/{analysis_run_id}` | Poll one analysis run's status and per-stage progress.       |
| GET    | `/api/v1/decisions/{id}/experiments` | List the experiments recommended for a decision.                             |
| GET    | `/api/v1/decisions/{id}/experiment-results` | List every experiment result submitted for a decision.                |
| GET    | `/api/v1/experiments/{experiment_id}` | Fetch a single experiment by id.                                             |
| POST   | `/api/v1/experiments/{experiment_id}/results` | Submit an experiment's observed outcome; triggers re-evaluation.      |
| GET    | `/api/v1/experiments/{experiment_id}/results` | List results submitted for one experiment.                            |
| GET    | `/api/v1/decisions/{id}/external-evidence` | List external research findings for a decision (if research is enabled). |
| GET    | `/api/v1/ready`                | Readiness check - reports whether DynamoDB (required) and the research provider (optional) are reachable. |

### Listing and pagination

`GET /api/v1/decisions` uses DynamoDB's native pagination — there is no
offset-based paging. A response looks like:

```json
{
  "items": [ { "...": "decision" } ],
  "next_cursor": "eyJQSyI6ICJVU0VSI2xvY2FsLWRldi11c2VyIn0="
}
```

Pass `next_cursor` back as the `cursor` query parameter to fetch the next
page. `next_cursor: null` means there are no more results. The cursor is an
opaque, base64-encoded token wrapping DynamoDB's `LastEvaluatedKey` — treat
it as a black box, not something to parse or construct.

### Optimistic concurrency

`PATCH` accepts an optional `expected_updated_at` field. If provided, the
update is rejected with `409 Conflict` when the stored decision's
`updated_at` no longer matches — i.e. someone else changed it since you last
read it. Omit the field to update unconditionally.

### Decision status values

`draft`, `queued`, `analyzing`, `completed`, `needs_validation`, `archived`.
Only `draft` (on create) and manual `PATCH` transitions are reachable
today — the rest of the lifecycle is driven by the analysis pipeline, which
doesn't exist yet.

## 8. Evidence ingestion

Evidence is a document (currently PDF, DOCX, or TXT) uploaded against a
decision. Uploading extracts readable text and basic metadata - it does
**not** run any semantic analysis, embeddings, or AI on the content. That's
a later step.

### Uploading

```
POST /api/v1/decisions/{decision_id}/evidence
Content-Type: multipart/form-data; boundary=...

file: <the document>
```

The decision must exist and belong to the caller (same ownership check as
the decision routes) or the upload is rejected with `404` before any file
processing happens. The response is the created `Evidence` record:

```json
{
  "id": "…",
  "decision_id": "…",
  "title": "supplier-quote.pdf",
  "source_type": "document",
  "filename": "supplier-quote.pdf",
  "file_type": "pdf",
  "size_bytes": 48213,
  "page_count": 3,
  "content_reference": "extracted text, bounded to 20,000 characters…",
  "content_truncated": false,
  "storage_key": "5e2c…-….pdf",
  "created_at": "…"
}
```

`content_reference` holds extracted text up to a bounded length
(`MAX_CONTENT_REFERENCE_CHARS` = 20,000 characters in
`app/services/evidence.py`) so an evidence record stays metadata-sized
rather than duplicating an entire large document into DynamoDB.
`content_truncated` is `true` if the source text was longer than that.

### Validation and security

- **Extension allow-list.** Only `.pdf`, `.docx`, `.txt` by default
  (`ALLOWED_EVIDENCE_EXTENSIONS`). Anything else is rejected with `415`.
- **Content sniffing.** The claimed extension is checked against the file's
  actual leading bytes (PDF's `%PDF-` signature, DOCX's zip signature) -
  a `.pdf` extension on non-PDF bytes is rejected with `415` rather than
  trusting the client-supplied filename/MIME type.
- **Size limit.** Files over `MAX_UPLOAD_SIZE_BYTES` (10 MB by default) are
  rejected with `413`. Empty files are rejected with `415`.
- **Safe filenames.** The original filename is used only for display
  (`filename`/`title` fields). The file is always written to storage under
  a fresh, server-generated `<uuid>.<extension>` name - the client's
  filename never reaches the filesystem. Directory components (`../`,
  backslash paths) are stripped before even the display name is stored.
- **Path traversal.** `LocalStorageBackend` independently verifies every
  resolved path stays inside its configured storage root before any
  read/write/delete, as a second guard beyond the safe-filename generation.
- **No execution.** Uploaded files are only ever read as bytes for parsing
  or storage - they are never executed, imported, or passed to a shell.
- **No content logging.** Application logs never include document text or
  filenames' full paths - only ids, decision ids, file type, and size.

### Storage backend

`app/services/storage.py` defines a small `StorageBackend` interface
(`save` / `read` / `delete`, keyed by an opaque storage key) with one
implementation today, `LocalStorageBackend`, which writes to
`LOCAL_STORAGE_DIR` on disk and needs no AWS credentials. Selecting
`STORAGE_BACKEND=s3` today raises `NotImplementedError` - an S3-backed
implementation can be added later behind the same interface without any
calling code changing.

### Parsing

`app/services/document_parser.py` dispatches on file extension to a small
extractor per format:

| Format | Library     | Extracts                          |
| ------- | ------------ | ------------------------------------ |
| PDF     | `pypdf`      | Concatenated per-page text, page count |
| DOCX    | `python-docx`| Paragraph text                        |
| TXT     | stdlib       | Raw text (UTF-8, BOM-tolerant)        |

Adding a new format (or OCR for scanned images/photos of documents) later
means adding one more extractor function and one more dispatch branch -
callers in `app/services/evidence.py` don't need to change.

## 9. Agent foundation: Decision Analyzer

`POST /api/v1/decisions/{decision_id}/analyze` runs the **Decision
Analyzer**, the first agent in what will eventually be an eight-agent
pipeline (Decision Analyzer → Assumption Hunter → Blindspot Hunter →
Evidence Agent → Devil's Advocate → Regret Simulator → Threshold Engine →
Experiment Planner). Only the Decision Analyzer is implemented so far.

### What it does

The Decision Analyzer reads the decision's stated title, description,
desired outcome, budget, timeline, location, risk tolerance, beliefs, and
any evidence already uploaded for it - then produces a structured
first-pass understanding: what kind of decision this is, its primary goal,
its constraints, success criteria, key variables, and a set of initial
assumptions and unknowns. It does **not** make the decision, does **not**
fabricate facts or sources it wasn't given, and never exposes its internal
reasoning or a chain-of-thought transcript - only the final structured
result defined in `app/agents/schemas.py::DecisionAnalysis`.

Every claim in its output is classified as exactly one of `fact`,
`assumption`, or `unknown` - this is enforced by the system prompt (see
`app/agents/decision_analyzer.py::SYSTEM_PROMPT`) and by the response
schema itself.

### How it's built

- **A real agent, not a mocked function.** `build_decision_analyzer()`
  constructs an actual `strands.Agent` from the
  [Strands Agents SDK](https://strandsagents.com/) (`strands-agents` on
  PyPI), configured with `structured_output_model=DecisionAnalysis` so the
  SDK itself validates the model's response against that Pydantic schema
  before returning it.
- **Amazon Bedrock as the model provider.** `app/agents/config.py`
  constructs a `strands.models.BedrockModel` from `BEDROCK_MODEL_ID` and
  `AWS_REGION` - no API keys are constructed here; `BedrockModel` resolves
  AWS credentials itself via boto3's standard provider chain, exactly like
  the DynamoDB layer.
- **Orchestration, not direct calls.** Routes never call the agent
  directly. The flow is always:

  ```
  API route -> AnalysisOrchestrator -> Decision Analyzer agent
            -> structured DecisionAnalysis -> AnalysisRepository -> DynamoDB
  ```

  `app/agents/orchestrator.py::AnalysisOrchestrator` is the only thing that
  invokes the agent, and the agent never touches a repository or DynamoDB
  directly.

### Workflow

1. Load the decision from DynamoDB via `DecisionRepository`, verifying
   ownership (a decision belonging to another user, or a missing decision,
   both surface as a plain `404`).
2. Load any evidence already uploaded for that decision via
   `EvidenceRepository`.
3. Create an `AnalysisRun` record (`status=queued`) via
   `AnalysisRepository`.
4. Build an `AnalysisContext` (see `app/agents/context.py`) holding the
   decision and evidence - this is the shared object future agents in the
   same run would read from; only the Decision Analyzer's slice is
   populated today.
5. Transition the run to `running`, then invoke the Decision Analyzer.
6. Independently re-validate the returned structured output against the
   `DecisionAnalysis` schema (on top of the SDK's own validation) - see
   [Structured output validation](#structured-output-validation) below.
7. Persist the validated result on the `AnalysisRun` and transition it to
   `completed`.
8. On any agent/model failure, timeout, or invalid output, transition the
   run to `failed` with a safe, generic error message instead - the
   underlying provider error is logged server-side only, never returned to
   the caller.
9. Return `{ analysis_run_id, decision_id, status }` to the caller.

This step's implementation is synchronous - the API call blocks until the
run reaches `completed` or `failed`. There is no task queue and no polling
endpoint yet; the response IS the final result.

### Analysis run status

`queued` → `running` → `completed`, or `running` → `failed` on error. These
are the same `AnalysisRunStatus` values introduced in Step 2
(`app/schemas/decision_resources.py`), now actually driven by a real
pipeline run instead of only existing as a schema.

### Structured output validation

The Strands SDK validates the model's raw response against
`DecisionAnalysis` before returning it as `result.structured_output`. The
orchestrator re-validates that result independently
(`AnalysisOrchestrator._validate_analysis`) as a second, explicit check -
if the model produced something that doesn't conform, the run is marked
`failed` rather than a malformed object ever being persisted or returned.

### Cost and performance

- Exactly one model call per `/analyze` request - no retries-by-default
  loop, no speculative multi-agent fan-out (only one agent exists).
- A configurable timeout (`BEDROCK_INVOKE_TIMEOUT_SECONDS`, default 60s)
  bounds how long a single call can block a request.
- No streaming - the SDK's structured-output path returns one complete
  result, which matches this endpoint's synchronous, non-streaming
  contract.

## 10. DynamoDB architecture

### Single-table design

Everything lives in one table (`regret-engine` by default), partitioned so
that fetching everything about a decision is always a single `Query` on its
partition key — never a `Scan`.

| Item                | PK                       | SK                              |
| -------------------- | ------------------------- | ---------------------------------- |
| Decision             | `DECISION#<decision_id>`  | `METADATA`                         |
| Assumption           | `DECISION#<decision_id>`  | `ASSUMPTION#<assumption_id>`       |
| Blindspot             | `DECISION#<decision_id>`  | `BLINDSPOT#<blindspot_id>`         |
| Evidence (metadata)   | `DECISION#<decision_id>`  | `EVIDENCE#<evidence_id>`           |
| Scenario              | `DECISION#<decision_id>`  | `SCENARIO#<scenario_id>`           |
| Threshold             | `DECISION#<decision_id>`  | `THRESHOLD#<threshold_id>`         |
| Experiment            | `DECISION#<decision_id>`  | `EXPERIMENT#<experiment_id>`       |
| Analysis run          | `DECISION#<decision_id>`  | `ANALYSIS#<run_id>`                |

A **GSI named `GSI1`** exists solely to list a user's decisions (the one
access pattern that needs to fan out *across* decisions rather than *within*
one):

| Attribute  | Value                                          |
| ----------- | ------------------------------------------------- |
| `GSI1PK`    | `USER#<user_id>`                                  |
| `GSI1SK`    | `DECISION#<created_at_iso>#<decision_id>`         |

Only the decision item carries `GSI1PK`/`GSI1SK` — child entities don't need
to be listed across decisions, so they aren't indexed there.

A second GSI, **`GSI2`**, exists solely so a piece of evidence can be looked
up by its own id alone (`GET`/`DELETE /api/v1/evidence/{evidence_id}` don't
carry the parent decision id):

| Attribute  | Value                    |
| ----------- | -------------------------- |
| `GSI2PK`    | `EVIDENCE#<evidence_id>`   |
| `GSI2SK`    | `EVIDENCE#<evidence_id>`   |

Only evidence items carry `GSI2PK`/`GSI2SK`.

### Access patterns this supports without a scan

| # | Pattern                              | How                                                   |
| - | -------------------------------------- | -------------------------------------------------------- |
| 1 | Get a decision by user + id            | `GetItem` on `PK=DECISION#<id>, SK=METADATA`, then an ownership check against `user_id` in the service layer |
| 2 | List a user's decisions                | `Query` on `GSI1PK=USER#<user_id>`, paginated            |
| 3 | Get all assumptions for a decision      | `Query` on `PK=DECISION#<id>, SK begins_with ASSUMPTION#` |
| 4 | Get all blindspots for a decision       | `Query` on `PK=DECISION#<id>, SK begins_with BLINDSPOT#`  |
| 5 | Get evidence metadata for a decision    | `Query` on `PK=DECISION#<id>, SK begins_with EVIDENCE#`   |
| 6 | Get all thresholds for a decision       | `Query` on `PK=DECISION#<id>, SK begins_with THRESHOLD#`  |
| 7 | Get all experiments for a decision      | `Query` on `PK=DECISION#<id>, SK begins_with EXPERIMENT#` |
| 8 | Get analysis runs for a decision        | `Query` on `PK=DECISION#<id>, SK begins_with ANALYSIS#`   |
| 9 | Update decision status                  | `UpdateItem` on the decision's key, conditioned on existence (and optionally `updated_at`) |
| 10| Update analysis status                  | `UpdateItem` on the analysis run's key, conditioned on existence |

Repository methods for patterns 3–8 exist today (`DecisionRepository.list_assumptions`,
etc., plus `EvidenceRepository` and `AnalysisRepository`) but aren't wired to
public routes yet — there's nothing to populate them until the analysis
pipeline exists.

### Local development

Two supported paths, your choice:

**Option A — point straight at real AWS.** Leave `AWS_ENDPOINT_URL` unset,
configure AWS credentials normally (e.g. `aws configure`, or environment
variables), set `AWS_REGION`/`DYNAMODB_TABLE_NAME`, then create the table
once:

```powershell
python scripts/create_table.py
```

**Option B — use a local DynamoDB-compatible endpoint.** Run one locally
(DynamoDB Local, or moto's server mode via `pip install "moto[server]"` then
`python -m moto.server -p 5001`), set `AWS_ENDPOINT_URL=http://127.0.0.1:5001`
(or wherever it's listening), set any placeholder AWS credentials (moto
doesn't validate them, but boto3 still requires *something* to be present),
then run the same table-creation script.

Either way, `scripts/create_table.py` is idempotent — it checks whether the
table already exists before creating it, and is never called automatically
by the application itself.

### Required IAM permissions

For the API to operate against a real table, its execution role needs at
least:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine",
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine/index/GSI1",
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine/index/GSI2"
      ]
    }
  ]
}
```

Table creation (`dynamodb:CreateTable`) is a separate, one-time
administrative action and is intentionally not required by the running
application — it's only exercised by `scripts/create_table.py` during setup.

## 11. Production hardening (Step 12)

This section covers reliability/operability concerns added on top of the
product logic above - none of it changes agent behavior or the pipeline's
dependency order.

### Idempotency

`POST /decisions/{id}/analyze` is idempotent: if a decision already has an
active (`queued`/`running`) analysis run, a second call returns that same
run (same `analysis_run_id`) instead of starting a duplicate, expensive
pipeline (`AnalysisOrchestrator.run_analysis` →
`AnalysisRepository.get_active_run`). A run stuck `running` past
`ANALYSIS_MAX_DURATION_SECONDS + ANALYSIS_LOCK_GRACE_SECONDS` (e.g. the
process crashed mid-run) is treated as abandoned rather than active, so a
decision is never permanently unable to be re-analyzed.

A process-wide semaphore (`MAX_CONCURRENT_ANALYSES`) additionally bounds
how many analysis pipelines (across *different* decisions) run at once in
one process - a lightweight guard against exhausting Bedrock capacity, not
a distributed rate limiter.

Submitting a second result for an already-`completed` experiment
(`POST /experiments/{id}/results`) is rejected with `409 Conflict` -
enforced by a DynamoDB conditional write on the experiment's status
transition (`DecisionRepository.update_experiment_status(...,
require_not_completed=True)`), so two concurrent submissions for the same
experiment can never both succeed.

### Analysis status endpoint

`GET /decisions/{id}/analysis/{analysis_run_id}` returns:

```json
{
  "analysis_run_id": "…",
  "decision_id": "…",
  "status": "running",
  "current_stage": "evidence_agent",
  "stage_statuses": {
    "decision_analyzer": "completed",
    "assumption_hunter": "completed",
    "blindspot_hunter": "completed",
    "research_agent": "unavailable",
    "evidence_agent": "running",
    "devils_advocate": "pending",
    "regret_simulator": "pending",
    "threshold_engine": "pending",
    "experiment_planner": "pending"
  },
  "created_at": "…",
  "updated_at": "…",
  "error_message": null
}
```

Never includes chain-of-thought, raw prompts, or a stage's full structured
output - only execution metadata. Use the decision's own child-entity
endpoints (assumptions, thresholds, experiments, etc.) to read actual
findings once a run completes.

### Standardized error responses

Every error response uses one shape:

```json
{
  "error": { "code": "ANALYSIS_NOT_FOUND", "message": "…", "request_id": "…" },
  "detail": "…"
}
```

`code` is stable and machine-readable; `message`/`detail` carry the same
human-readable text (`detail` kept only for backward compatibility);
`request_id` matches the `X-Request-ID` response header, so a report can
be correlated with server-side logs. Never includes stack traces, AWS
internals, or a raw provider error message (see `app/core/errors.py`).

### Request ids and logging

Every request gets an `X-Request-ID` (echoed back on the response; a
caller-supplied one is preserved if well-formed) via
`app.core.request_context` and `app.main`'s request-id middleware. Every
log line during that request automatically includes it
(`app/core/logging.py`), so a single request's activity is correlatable
end to end without threading an id through every function call manually.
Logs never include AWS credentials, API keys, full uploaded documents,
chain-of-thought, or prompts containing private user content.

### Health vs. readiness

`GET /api/v1/health` is a pure liveness check - it never fails because an
optional dependency (the external research provider) is unavailable.
`GET /api/v1/ready` additionally probes DynamoDB (required) and reports
the research provider's configured status (optional, informational only);
overall `status` is `"degraded"` only if a *required* dependency is
unreachable.

### Production configuration validation

At startup, if `APP_ENV=production`, `Settings.validate_for_production()`
requires `AWS_REGION`, `DYNAMODB_TABLE_NAME`, `BEDROCK_MODEL_ID`, and
explicit (non-`*`) `CORS_ALLOWED_ORIGINS` to be set, and raises
`RuntimeError` (crashing startup) if any are missing - an
under-configured production process should never silently start serving
traffic. Development mode never requires any of this; sensible defaults
apply.

### Upload handling

Evidence uploads are now read in bounded 1 MB chunks
(`app/api/routes/evidence.py::_read_bounded`), rejecting an oversized file
as soon as it crosses `MAX_UPLOAD_SIZE_BYTES` rather than first buffering
the entire body into memory - `EvidenceService.upload_evidence` still
independently re-checks the final size as defense in depth.

## 12. Docker

A `Dockerfile`/`.dockerignore` package the API for containerized
deployment:

```powershell
docker build -t regret-engine-backend .
docker run -p 8000:8000 --env-file .env regret-engine-backend
```

- Base image: `python:3.12-slim`.
- Runs as a non-root user (`regret`).
- No secrets are baked into the image - all configuration is
  environment-driven at runtime, exactly like running locally.
- Includes a container `HEALTHCHECK` against `GET /api/v1/health`.
- In AWS (ECS/Fargate, App Runner, EC2, etc.), prefer attaching an IAM
  role to the running task/instance instead of passing
  `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` - boto3 (and Strands'
  `BedrockModel`) picks up the role automatically via the same credential
  provider chain used everywhere else in this codebase.

## 13. AWS setup

Minimum AWS resources to run this backend against real AWS (as opposed to
the moto-mocked test suite, which needs none of this):

| Resource | Required? | Notes |
| --- | --- | --- |
| DynamoDB table | **Required** | See [DynamoDB architecture](#10-dynamodb-architecture) - create via `python scripts/create_table.py`, or point `AWS_ENDPOINT_URL` at a local DynamoDB-compatible endpoint for development instead. |
| Amazon Bedrock model access | **Required** to actually call `/analyze` against a real model | Enable model access for `BEDROCK_MODEL_ID` in the target account/region. The rest of the API (decisions, evidence, experiments) works without this. |
| S3 bucket | Optional (not implemented yet) | Reserved for a future S3-backed `StorageBackend`; `STORAGE_BACKEND=local` needs no AWS resources at all. |
| External research provider | Optional | The built-in DuckDuckGo HTML provider (`RESEARCH_PROVIDER=http`) needs no AWS resource or API key - just outbound HTTPS access. |

### IAM (least privilege)

The running application's role/user needs only:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynamoDBTableAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query"
      ],
      "Resource": [
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine",
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine/index/GSI1",
        "arn:aws:dynamodb:<region>:<account-id>:table/regret-engine/index/GSI2"
      ]
    },
    {
      "Sid": "BedrockInvoke",
      "Effect": "Allow",
      "Action": ["bedrock:InvokeModel"],
      "Resource": "arn:aws:bedrock:<region>::foundation-model/<bedrock-model-id>"
    }
  ]
}
```

- Never grant `AdministratorAccess` or a wildcard `dynamodb:*`/`bedrock:*`
  to the running application.
- `dynamodb:CreateTable` is intentionally **not** included - table
  provisioning is a separate, deliberate one-time administrative action
  (`scripts/create_table.py`), never something the running API does on its
  own.
- If/when an S3-backed `StorageBackend` is added, its role should be
  scoped to `s3:GetObject`/`s3:PutObject`/`s3:DeleteObject` on the specific
  bucket/prefix only - never account-wide S3 access.
- If a future research provider requires an API key
  (`RESEARCH_API_KEY`), treat it exactly like any other secret: environment
  variable only, never committed, never logged.

### AWS credential resolution (local vs. production)

Never set `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` in `.env` or
anywhere in source - boto3 (and Strands' `BedrockModel`) resolves
credentials itself via the standard provider chain:

- **Local development**: an AWS CLI profile (`aws configure`) or
  environment variables in your own shell (never committed to `.env`).
- **Production on AWS**: an IAM role attached to the compute environment
  (ECS task role, EC2 instance profile, Lambda execution role, etc.) -
  this is the preferred approach; no credentials ever touch disk or an
  environment variable at all.

## 14. Current limitations

- **No vector search.** Extracted evidence text is stored as plain text,
  not embeddings - there's no semantic search over evidence.
- **No S3-backed storage yet.** Evidence files live on local disk
  (`LocalStorageBackend`) behind an interface designed so an S3
  implementation can be added later without changing callers.
- **No OCR/image support yet.** Only PDF, DOCX, and TXT are parseable
  today; `document_parser.py` is structured so an image/OCR extractor can
  be added as one more dispatch branch later.
- **No real authentication.** Every request is currently attributed to a
  single fixed placeholder user id (`DEFAULT_USER_ID`,
  `app/dependencies/auth.py`). The data model and every access pattern are
  already user-scoped, and every route/dependency is structured so real
  auth can be inserted later without rewriting routes - just replacing
  that one dependency.
- **Synchronous analysis.** `/analyze` still blocks the HTTP request until
  the entire pipeline (all ~9 sequential agent stages) reaches a terminal
  status. There is no background task queue yet - `GET
  /decisions/{id}/analysis/{run_id}` exists for status *inspection*, but
  nothing currently lets a caller submit `/analyze` and disconnect before
  it finishes. `ANALYSIS_MAX_DURATION_SECONDS`/`ANALYSIS_LOCK_GRACE_SECONDS`
  and the idempotency guard exist specifically because of this constraint.
- **No infrastructure-as-code.** The Dockerfile packages the app; nothing
  yet provisions ECS/Fargate/App Runner/etc. automatically.
- **No production deployment.** This has been hardened for readiness, not
  actually deployed anywhere yet.

## 15. Planned architecture

Roughly, in upcoming steps:

- Move `/analyze` to a genuinely asynchronous background-execution model
  (submit and disconnect, poll `GET /decisions/{id}/analysis/{run_id}` for
  completion) now that the pipeline has ~9 sequential agent stages long
  enough to matter.
- Add an S3-backed `StorageBackend` implementation for evidence, behind the
  interface that already exists.
- Add OCR/image support to `document_parser.py` for scanned documents.
- Replace the placeholder user id with real authentication/authorization.
- Add infrastructure-as-code and an actual production deployment.

None of the above is implemented yet — this README will be updated as each
step lands.

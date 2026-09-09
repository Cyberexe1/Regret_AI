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
- **Step 4** (this step): the foundation for the AI agent pipeline - a real
  [Strands Agents SDK](https://strandsagents.com/) agent (the **Decision
  Analyzer**) running on **Amazon Bedrock**, orchestrated behind a new
  `/analyze` endpoint. Only this one agent exists so far.

No Assumption Hunter, Blindspot Hunter, Evidence Agent, Devil's Advocate,
Regret Simulator, Threshold Engine, Experiment Planner, or vector search
yet — see [Current limitations](#11-current-limitations) below.

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
| `DEFAULT_USER_ID`        | `local-dev-user`                                | Placeholder identity used until real authentication exists. See [Current limitations](#11-current-limitations). |
| `STORAGE_BACKEND`        | `local`                                         | Evidence file storage backend. Only `local` is implemented; `s3` is reserved for later. |
| `LOCAL_STORAGE_DIR`      | `./data/evidence`                               | Where evidence files are written when using the `local` backend. Requires no AWS credentials. |
| `MAX_UPLOAD_SIZE_BYTES`  | `10485760` (10 MB)                              | Maximum accepted evidence upload size.                                              |
| `ALLOWED_EVIDENCE_EXTENSIONS` | `.pdf,.docx,.txt`                          | Comma-separated allow-list of accepted upload extensions.                           |
| `BEDROCK_MODEL_ID`       | `global.anthropic.claude-sonnet-4-6`            | Bedrock model id the Decision Analyzer uses. Override per account/region if needed. |
| `BEDROCK_INVOKE_TIMEOUT_SECONDS` | `60`                                     | Wall-clock budget for one agent model call before it's treated as a failure.        |

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
| POST   | `/api/v1/decisions/{id}/analyze`  | Run the Decision Analyzer for a decision. See [Agent foundation](#9-agent-foundation-decision-analyzer). |

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

## 11. Current limitations

- **Only one agent exists.** The Decision Analyzer is implemented; the
  Assumption Hunter, Blindspot Hunter, Evidence Agent, Devil's Advocate,
  Regret Simulator, Threshold Engine, and Experiment Planner do not exist
  yet. `AnalysisContext` and the `AnalysisOrchestrator` workflow are shaped
  to add them as later steps in the same pipeline.
- **Synchronous only.** `/analyze` blocks until the run finishes. There is
  no background task queue and no polling endpoint - fine for one agent
  and a hackathon-scale prototype, but will need revisiting once the
  pipeline has multiple sequential agent calls.
- **No vector search.** Extracted evidence text is stored as plain text,
  not embeddings - there's no semantic search over evidence yet.
- **No S3-backed storage yet.** Evidence files live on local disk
  (`LocalStorageBackend`) behind an interface designed so an S3
  implementation can be added later without changing callers.
- **No OCR/image support yet.** Only PDF, DOCX, and TXT are parseable
  today; `document_parser.py` is structured so an image/OCR extractor can
  be added as one more dispatch branch later.
- **No real authentication.** Every request is currently attributed to a
  single fixed placeholder user id (`DEFAULT_USER_ID`,
  `app/dependencies/auth.py`). The data model and every access pattern are
  already user-scoped so swapping in real auth later shouldn't require a
  schema change — just replacing that one dependency.
- **No AWS deployment.** This runs locally only for now.

## 12. Planned architecture

Roughly, in upcoming steps:

- Add the remaining agents (Assumption Hunter, Blindspot Hunter, Evidence
  Agent, Devil's Advocate, Regret Simulator, Threshold Engine, Experiment
  Planner) as additional steps inside `AnalysisOrchestrator.run_analysis`,
  each populating its slice of `AnalysisContext` and its own repository
  (`list_assumptions`, `list_blindspots`, etc. already exist on
  `DecisionRepository` from Step 2, just waiting for something to write
  into them).
- Move decision status transitions (`draft` → `queued` → `analyzing` → ...)
  to track the analysis run's actual progress once there are multiple
  sequential agent steps to reflect.
- Revisit the synchronous `/analyze` contract once the pipeline has enough
  sequential agent calls that a single request blocking on all of them
  stops being reasonable - likely a background task plus a polling/status
  endpoint, without introducing a heavy queue system prematurely.
- Add an S3-backed `StorageBackend` implementation for evidence, behind the
  interface that already exists.
- Add OCR/image support to `document_parser.py` for scanned documents.
- Move decision status transitions (`draft` → `queued` → `analyzing` → ...)
  into the analysis pipeline as real, observable state changes.
- Replace the placeholder user id with real authentication/authorization.
- Add deployment infrastructure (containerization, AWS hosting) once the
  service is feature-complete enough to deploy.

None of the above is implemented yet — this README will be updated as each
step lands.

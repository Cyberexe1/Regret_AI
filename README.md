# REGRET ENGINE

**Know what could make your decision fail.**

> Most AI decision tools tell you what they think you should do.
>
> REGRET ENGINE doesn't.
>
> It discovers the conditions under which your decision could fail, identifies the thresholds that matter, and tells you the cheapest experiment you can run before committing.

REGRET ENGINE is decision *validation* infrastructure, not a chatbot and not a recommendation engine. It never tells a user what to decide. It runs a decision through a structured, multi-agent pipeline on Amazon Bedrock and returns exactly one thing a generic AI assistant doesn't: **the specific, falsifiable condition under which this decision would turn out to be a mistake**, plus the cheapest real-world test that would tell you whether that condition is true.

```
Decision → Failure Conditions → Thresholds → Experiment → Re-evaluation
```

---

## Table of contents

1. [Overview](#1-overview)
2. [Problem](#2-problem)
3. [Solution](#3-solution)
4. [Why REGRET ENGINE is different](#4-why-regret-engine-is-different)
5. [How it works](#5-how-it-works)
6. [Multi-agent architecture](#6-multi-agent-architecture)
7. [Agent responsibilities](#7-agent-responsibilities)
8. [Experiment + re-evaluation loop](#8-experiment--re-evaluation-loop)
9. [Technical architecture](#9-technical-architecture)
10. [AWS services](#10-aws-services)
11. [Strands Agents SDK](#11-strands-agents-sdk)
12. [Evidence and source grounding](#12-evidence-and-source-grounding)
13. [Security considerations](#13-security-considerations)
14. [Local development](#14-local-development)
15. [Environment variables](#15-environment-variables)
16. [Running the frontend](#16-running-the-frontend)
17. [Running the backend](#17-running-the-backend)
18. [Running tests](#18-running-tests)
19. [Production deployment](#19-production-deployment)
20. [Project structure](#20-project-structure)
21. [Demo walkthrough](#21-demo-walkthrough)
22. [From AI opinion to evidence loop](#22-from-ai-opinion-to-evidence-loop)
23. [Limitations](#23-limitations)
24. [Future improvements](#24-future-improvements)
25. [License](#25-license)

---

## 1. Overview

REGRET ENGINE takes a decision a person is actually facing — described in their own words, with real constraints and real uploaded evidence — and runs it through nine sequential, specialized AI agents on Amazon Bedrock, orchestrated with the [Strands Agents SDK](https://strandsagents.com/). The output is not advice. It's a structured breakdown of the decision's hidden assumptions, blindspots, adversarial counter-arguments, regret scenarios, the specific numeric or qualitative *threshold* that would make it fail, and one concrete, low-cost experiment to run before committing. When the user runs that experiment and reports what actually happened, REGRET ENGINE deterministically re-evaluates the decision against the new evidence — no further model call required for that step.

## 2. Problem

Most high-stakes personal and small-business decisions — "should I take this job," "should I invest in this business," "should I sign this lease" — get made on gut feeling, a friend's opinion, or a single AI chat that produces a confident-sounding paragraph. That paragraph is an opinion. It doesn't tell the decision-maker what would have to be true for the decision to work, what evidence is actually missing, or what they could check *before* spending the money or the time. When the decision goes wrong, it's usually not because the idea was bad — it's because nobody identified the one variable that mattered until it was too late.

## 3. Solution

REGRET ENGINE reframes "should I do this?" into a sequence of falsifiable questions:

- What does this decision depend on being true? (**assumptions**)
- What important question is nobody asking? (**blindspots**)
- What does the evidence I already have actually say? (**evidence grounding**)
- What's the strongest argument against this? (**adversarial challenge**)
- What specific way could this go wrong? (**regret scenarios**)
- What's the exact tipping point — the number or condition — that separates "this works" from "this fails"? (**threshold**)
- What's the cheapest real test I can run to find out, before committing fully? (**experiment**)
- Given what the test actually showed, does the decision look stronger, weaker, or still unresolved? (**re-evaluation**)

Each question is answered by a distinct agent with a narrow, auditable job, consuming only the *structured, validated output* of the agents before it — never re-reading the user's raw text from scratch, and never inventing facts it wasn't given.

## 4. Why REGRET ENGINE is different

- It never outputs "you should do this" or "you should not do this." It outputs a breaking condition and a way to test it.
- Every claim is traceable to either the user's own stated decision, the user's own uploaded evidence, or an explicit "assumption"/"unknown" classification — never presented as fact when it isn't one.
- The threshold and experiment stages are the center of the product, not a bolt-on feature. A decision report that skipped straight to "here's a risk score" would defeat the point.
- Re-evaluation after an experiment result is deterministic code (`app/services/re_evaluation_service.py`), not another model call re-guessing the outcome — the system doesn't get to change its mind for no reason once real evidence exists.
- Agents pass typed, Pydantic-validated structured objects to each other and to storage — never raw conversational text — so every intermediate result is inspectable, storable, and testable on its own.

REGRET ENGINE does not claim to be the only tool that does any one of these things in isolation. What it addresses is the specific gap where AI decision tools stop at an opinion instead of producing a falsifiable, testable claim about reality.

## 5. How it works

```
User describes a decision + uploads evidence (optional)
        │
        ▼
POST /decisions/{id}/analyze
        │
        ▼
Nine-stage agent pipeline (Amazon Bedrock, via Strands Agents SDK)
        │
        ▼
Structured, persisted results: assumptions, blindspots, challenges,
regret scenarios, thresholds, and one recommended experiment
        │
        ▼
User runs the experiment in the real world, reports the result
        │
        ▼
POST /experiments/{id}/results
        │
        ▼
Deterministic re-evaluation (no model call) against the real threshold
        │
        ▼
Updated decision assessment: strengthened / weakened / unchanged /
inconclusive / requires_more_evidence
```

## 6. Multi-agent architecture

The pipeline is a fixed, sequential dependency order — every stage consumes the *already-persisted, id-bearing* output of the stages before it, never the user's raw text again and never another agent's raw prose:

```
Decision Analyzer
      ↓
Assumption Hunter
      ↓
Blindspot Hunter
      ↓
Research Agent  (optional, external evidence only — never blocks the pipeline)
      ↓
Evidence Agent
      ↓
Devil's Advocate
      ↓
Regret Simulator
      ↓
Threshold Engine
      ↓
Experiment Planner
      ↓
Decision Report  (assumptions, blindspots, challenges, regret scenarios, thresholds)
      ↓
Real-world Experiment  (run by the user, outside the system)
      ↓
Experiment Result submitted back
      ↓
Deterministic Re-evaluation
      ↓
Updated Decision Assessment
```

This exact order is implemented in `backend/app/agents/orchestrator.py` (`AnalysisOrchestrator.run_analysis`), stage by stage, each labeled with a comment (`# --- Stage 1: Decision Analyzer`, etc.). If any required stage fails, every stage after it is marked `skipped` and the run is marked `failed` with a safe, generic error — the raw provider error is logged server-side only, never returned to the caller. The Research Agent is the one exception: it's optional, and its failure or unavailability never fails the run.

## 7. Agent responsibilities

Every agent is a real `strands.Agent` (see [Strands Agents SDK](#11-strands-agents-sdk)) configured with a Pydantic `structured_output_model`, so the SDK itself validates the model's response before the orchestrator ever sees it. No agent exposes chain-of-thought; only the final structured result is ever returned or logged.

| Agent | Input | Output | Why it exists |
|---|---|---|---|
| **Decision Analyzer** (`decision_analyzer.py`) | The user's decision text (title, description, desired outcome, budget, timeline, beliefs) + any uploaded evidence | `DecisionAnalysis`: decision type, goal, constraints, success criteria, key variables, initial facts/assumptions/unknowns | First-pass structured understanding everything downstream builds on, instead of every later agent re-parsing the raw text itself |
| **Assumption Hunter** (`assumption_hunter.py`) | `DecisionAnalysis` + evidence | List of `Assumption`s, each with importance, confidence, and a `dependency`/`failure_consequence` | Surfaces what the decision quietly depends on being true |
| **Blindspot Hunter** (`blindspot_hunter.py`) | `DecisionAnalysis` + assumptions + evidence | List of `Blindspot`s: important unasked questions, with `why_it_matters` | Finds the question nobody thought to ask, distinct from an assumption already stated |
| **Research Agent** (`research_agent.py`, *optional*) | Assumptions + blindspots | `ExternalEvidence` findings from a real web search (DuckDuckGo HTML provider) | Adds independently-sourced external context when enabled — kept in its own vocabulary, never merged into user-uploaded evidence |
| **Evidence Agent** (`evidence_agent.py`) | Assumptions, blindspots, and the user's *actually uploaded* evidence | `EvidenceFinding`s: whether each piece of evidence supports, contradicts, or is insufficient for a specific claim | Grounds the analysis in what was actually provided — never treats silence as support |
| **Devil's Advocate** (`devils_advocate.py`) | Assumptions, blindspots, evidence findings | `Challenge`s: concrete, evidence-grounded counter-arguments with a severity rating | Forces the decision through an adversarial pass instead of only a supportive one |
| **Regret Simulator** (`regret_simulator.py`) | Assumptions, blindspots, evidence findings, challenges | `RegretScenario`s: specific failure conditions, trigger variables, and consequences | Converts abstract risk into a concrete "here's how this specifically goes wrong" story |
| **Threshold Engine** (`threshold_engine.py`) | All of the above | `Threshold`s: the exact variable, direction, and tipping-point value (numeric or qualitative) that would make the decision fail | The single most important artifact in the product — the falsifiable breaking condition |
| **Experiment Planner** (`experiment_planner.py`) | All of the above, including thresholds | An `Experiment`: hypothesis, target threshold, variable to test, steps, success/failure criteria, evidence to collect, and a `decision_rule` | Turns "this is risky" into "here's the cheapest thing to test before committing" |

## 8. Experiment + re-evaluation loop

Once an experiment is recommended, the user runs it in the real world (a pilot, a preorder campaign, a small-scale test) and submits the outcome:

```
POST /experiments/{experiment_id}/results
```

This is the only place in the product where an *observed*, real-world value enters the system. `app/services/re_evaluation_service.py` then:

1. Marks the experiment `completed` (a second submission is rejected with `409 Conflict` — enforced by a DynamoDB conditional write, not just an application check).
2. Compares the reported measured value against the target threshold's real bounds — deterministically, in code, never by asking a model to re-judge the outcome.
3. Produces a `decision_assessment` of `strengthened`, `weakened`, `unchanged`, `inconclusive`, or `requires_more_evidence`, plus a `key_learning` and a `recommended_next_step`.
4. Persists a `ReEvaluation` record retrievable via `GET /decisions/{id}/reevaluations`.

## 9. Technical architecture

```
Browser  →  Amazon CloudFront (CDN, HTTPS)  →  React + TypeScript (static, S3-hosted)
                                                        │
                                                        │ HTTPS, fetch()
                                                        ▼
                                              AWS App Runner  →  FastAPI
                                                                    │
                                              ┌─────────────────────┼─────────────────────┐
                                              ▼                     ▼                     ▼
                                         Amazon DynamoDB       Amazon S3         Strands Agents SDK
                                       (decisions, agent      (evidence bucket,        │
                                        results, runs)         reserved for future      ▼
                                                                 S3-backed storage)  Amazon Bedrock
```

See [`docs/architecture.md`](docs/architecture.md) for the full diagram (Mermaid source in [`docs/architecture.mmd`](docs/architecture.mmd)) and [`docs/agent-workflow.md`](docs/agent-workflow.md) for the reasoning-pipeline diagram separate from the infrastructure diagram.

The browser **never** calls DynamoDB, S3, or Bedrock directly — it only ever calls this backend's own HTTPS API. The backend is the only thing with an AWS IAM identity.

## 10. AWS services

| Service | What it's actually used for |
|---|---|
| **Amazon Bedrock** | Runs every agent in the pipeline. Model: Amazon Nova Pro, invoked via the cross-region inference profile `apac.amazon.nova-pro-v1:0`. |
| **AWS App Runner** | Hosts the containerized FastAPI backend. Pulls its image from a private ECR repo and assumes a dedicated IAM instance role — no AWS access keys ever exist in its environment variables. |
| **Amazon DynamoDB** | Single-table store for decisions, assumptions, blindspots, evidence metadata, challenges, regret scenarios, thresholds, experiments, experiment results, re-evaluations, and analysis-run status. See [Project structure](#20-project-structure) → backend README for the full key schema. |
| **Amazon S3** | A dedicated, fully private bucket (`regret-engine-evidence-*`) reserved for evidence storage; a *separate* private bucket + Amazon CloudFront (with Origin Access Control) serves the built React app as a static site. |
| **Amazon CloudFront** | Public HTTPS entry point for the frontend, backed by the private S3 bucket via OAC — the bucket itself has no public access. |
| **Amazon ECR** | Private, image-scanned, immutable-tag container registry for the backend's Docker image. |
| **AWS IAM** | Two purpose-built roles: an App Runner *instance* role (least-privilege — scoped DynamoDB table/index actions, the evidence bucket only, and the specific Bedrock inference profile + underlying model ARNs) and a separate App Runner *ECR access* role used only to pull the image. No `AdministratorAccess` anywhere. |

## 11. Strands Agents SDK

**REGRET ENGINE uses the Strands Agents SDK to orchestrate its decision-analysis agents.**

Every one of the nine pipeline stages is a real `strands.Agent` instance, not a hand-rolled prompt-and-parse function:

- `app/agents/config.py::get_bedrock_model()` constructs one process-wide `strands.models.BedrockModel`, shared by every agent, from `BEDROCK_MODEL_ID`/`AWS_REGION` — no credentials are constructed here; `BedrockModel` resolves AWS credentials itself via boto3's standard provider chain.
- Each agent file (`decision_analyzer.py`, `assumption_hunter.py`, `blindspot_hunter.py`, `research_agent.py`, `evidence_agent.py`, `devils_advocate.py`, `regret_simulator.py`, `threshold_engine.py`, `experiment_planner.py`) has a `build_<agent_name>()` function that constructs a `strands.Agent(model=..., system_prompt=..., structured_output_model=<a Pydantic schema from app/agents/schemas.py>)`, and a `run_<agent_name>()` function that calls `agent.invoke_async(prompt)`.
- `app/agents/orchestrator.py::AnalysisOrchestrator` is the *only* thing that ever invokes these agents — routes never call an agent directly, and agents never touch DynamoDB directly. The orchestrator independently re-validates every returned structured output against its Pydantic schema before persisting it, on top of the SDK's own validation.
- `app/agents/config.py::invoke_with_retry` wraps every Bedrock call with a narrow, capped retry — but only for the specific transient `botocore.exceptions.EventStreamError` occasionally seen from the provider; every genuine failure (timeout, validation, throttling, access-denied) still surfaces on the first attempt.

## 12. Evidence and source grounding

- User-uploaded evidence (PDF/DOCX/TXT) is parsed once (`app/services/document_parser.py`), stored with a bounded, non-fabricated text extract, and handed to the Evidence Agent — which is instructed to mark a claim `insufficient` rather than guess when the evidence doesn't actually address it.
- The optional Research Agent's external findings are kept in a completely separate vocabulary (`ExternalEvidence`, not `Evidence`) so user-provided and externally-sourced material are never silently conflated.
- Every `EvidenceFinding`/`Challenge`/`Experiment` that references an assumption, blindspot, or evidence id is checked against the *actual, already-persisted* ids the agent was given — a reference to an id the model wasn't given is dropped before persistence rather than stored as a dangling/fabricated link.

## 13. Security considerations

- **No AWS credentials in the frontend, ever.** The browser only ever calls this backend's own HTTPS API (`VITE_API_BASE_URL`) — never DynamoDB, S3, or Bedrock directly.
- **No AWS access keys anywhere in source, Docker images, or App Runner environment variables.** boto3 and the Strands SDK's `BedrockModel` resolve credentials exclusively through the standard provider chain — locally via an AWS CLI profile, in production via the App Runner instance's IAM role.
- **Least-privilege IAM.** The App Runner instance role is scoped to exactly the DynamoDB table + its two indexes, the one evidence S3 bucket, and the one Bedrock inference profile/model — never a wildcard, never `AdministratorAccess`.
- **Private storage.** Both S3 buckets (evidence, frontend) have Block Public Access fully enabled. The frontend bucket is reachable only through CloudFront via Origin Access Control; direct S3 access returns `403`.
- **Restricted CORS.** Production `CORS_ALLOWED_ORIGINS` is an explicit allow-list of the real frontend origin — never `*`.
- **Upload validation.** Extension allow-list, content-sniffing (magic-byte checks against the claimed extension), size limits, and server-generated storage filenames (the client's filename is never used on disk) — see the backend README's [Evidence ingestion](backend/README.md#8-evidence-ingestion) section.
- **No secrets in logs.** Logged errors are truncated and never include document content, prompts, or chain-of-thought.

## 14. Local development

Requirements: Python 3.12+, Node.js (for Vite/React), an AWS account with DynamoDB + Bedrock access (or point at a local DynamoDB-compatible endpoint for development without any AWS account at all — see the backend README).

```powershell
git clone <your-fork-or-clone-url>
cd Regret_AWS_Agent
```

## 15. Environment variables

Full, authoritative variable tables live in each app's own `.env.example` and README:

- Backend: [`backend/.env.example`](backend/.env.example), documented in [`backend/README.md`](backend/README.md#4-environment-setup)
- Frontend: [`frontend/.env.example`](frontend/.env.example)

**Never commit a real `.env` file.** Both are gitignored; only the `.env.example` placeholder files are tracked. **AWS credentials are never set as environment variables anywhere in this project** — not in the backend's `.env`, not in the frontend's `.env`, not in Docker, not in App Runner. boto3's standard credential provider chain (an AWS CLI profile locally, an IAM role in production) is the only supported way credentials ever reach this application.

## 16. Running the frontend

```powershell
cd frontend
npm install
npm run dev
```

Runs at `http://localhost:5173`, talking to a backend at `http://localhost:8000/api/v1` by default (`VITE_API_BASE_URL` in `.env.example`).

## 17. Running the backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python scripts/create_table.py    # one-time: creates the DynamoDB table
uvicorn app.main:app --reload --port 8000
```

macOS/Linux, the only difference is the venv activation step:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/create_table.py
uvicorn app.main:app --reload --port 8000
```

API docs at `http://127.0.0.1:8000/docs`. See [`backend/README.md`](backend/README.md) for the full setup, including how to run against a local DynamoDB-compatible endpoint instead of real AWS.

## 18. Running tests

```powershell
# Backend — no real AWS account, credentials, or network access required.
# Every test runs against moto's in-process DynamoDB mock, and every agent
# call site is patched so no test ever calls Amazon Bedrock.
cd backend
pytest
ruff check .

# Frontend
cd frontend
npm run test
npm run typecheck
npm run build
```

## 19. Production deployment

REGRET ENGINE is deployed and running:

```
Amazon CloudFront  →  private S3 bucket (React build)
        │
        ▼ HTTPS, browser fetch()
AWS App Runner  →  FastAPI  →  DynamoDB / S3 / Bedrock
```

Full deployment details — the exact resource names, IAM policies, redeploy commands, and cache/SPA-routing configuration — are documented in [`backend/README.md`](backend/README.md#deployed-on-aws-app-runner) and [`backend/README.md`](backend/README.md#production-frontend-deployment). Live URLs are listed in [`SUBMISSION.md`](SUBMISSION.md) once finalized for this submission.

## 20. Project structure

```
Regret_AWS_Agent/
├── backend/                 FastAPI application
│   ├── app/
│   │   ├── agents/          The 9-stage Strands Agents pipeline + orchestrator
│   │   ├── api/routes/      HTTP route handlers
│   │   ├── core/            Config, logging, error handling, request context
│   │   ├── dependencies/    FastAPI dependency-injection wiring
│   │   ├── repositories/    DynamoDB access layer
│   │   ├── research/        Optional external-research provider(s)
│   │   ├── schemas/         Pydantic request/response/stored-entity models
│   │   └── services/        Business logic (evidence, decisions, re-evaluation, storage)
│   ├── scripts/              One-off admin scripts (e.g. create_table.py)
│   ├── tests/                 pytest suite (moto-mocked, no real AWS needed)
│   └── README.md              Full backend documentation
├── frontend/                 React + TypeScript SPA (Vite)
│   └── src/
│       ├── api/               Centralized HTTP client + per-resource modules
│       ├── components/        UI components, grouped by feature area
│       ├── hooks/              Data-fetching and polling hooks
│       ├── lib/                 Pure helpers (formatting, tone mapping, report building)
│       ├── pages/               Route-level page components
│       └── types/                Shared TypeScript types
├── infra/                    AWS CLI-driven infrastructure config used to provision
│                                the deployment (IAM policies, App Runner/CloudFront configs)
├── docs/                     Architecture diagrams, demo script, demo data
├── LICENSE
├── SUBMISSION.md              Hackathon submission write-up
└── README.md                  This file
```

## 21. Demo walkthrough

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the full ~4-minute walkthrough and [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md) for the exact demo decision and evidence text used to reproduce it. In short: a founder asks whether to invest ₹5 lakh in a cloud kitchen, uploads a week of pilot-launch data, and REGRET ENGINE identifies the specific threshold (e.g. a repeat-order rate) that determines whether the business model actually works — then recommends the cheapest experiment to validate it before the full commitment.

## 22. From AI opinion to evidence loop

Traditional AI assistant:

```
Question → Answer
```

REGRET ENGINE:

```
Decision → Failure Condition → Threshold → Experiment → Evidence → Re-evaluation
```

The difference isn't that REGRET ENGINE uses more agents. It's that the product doesn't stop at an opinion — it produces a specific, falsifiable claim about reality (the threshold), a way to test that claim cheaply (the experiment), and a deterministic mechanism for updating the assessment once real evidence exists (the re-evaluation). This is designed to help someone validate an uncertain assumption *before* a costly commitment — it does not guarantee a better outcome, and it does not make the decision for them.

## 23. Limitations

- AI-generated analysis (assumptions, blindspots, challenges, regret scenarios, thresholds, experiments) can be wrong or incomplete — it reflects what the model inferred from what it was given, not ground truth.
- A threshold can remain `provisional` or qualitative (no numeric value) when the available evidence doesn't support deriving a specific number — the system never fabricates one to look more concrete.
- The Experiment Planner can legitimately recommend zero experiments if it judges that nothing in the analysis justifies a well-designed test yet, rather than inventing generic advice ("talk to customers") to fill the slot.
- External research quality (when enabled) depends entirely on what the provider's search actually returns — it can find nothing relevant, and the system reports that honestly rather than filling the gap.
- Experiment recommendations and re-evaluations are decision-support, never guarantees — REGRET ENGINE does not, and is explicitly designed not to, make an irreversible decision automatically on the user's behalf.
- Evidence storage currently uses the container's local disk, not Amazon S3, even though an S3 bucket is provisioned for it — the `StorageBackend` interface supports adding an S3 implementation later without changing any calling code, but that implementation doesn't exist yet.
- There is no authentication yet; every request is attributed to a single placeholder user id. The data model and every access pattern are already user-scoped so real auth can be added later without rewriting routes.
- `/analyze` is currently synchronous — the HTTP request blocks until the full ~9-stage pipeline finishes (with generous timeouts and an idempotency guard against duplicate runs), rather than a submit-and-poll background job model.

## 24. Future improvements

- An S3-backed `StorageBackend` implementation for evidence, behind the interface that already exists.
- Move `/analyze` to a genuinely asynchronous, submit-and-poll execution model now that the pipeline has grown to ~9 sequential stages.
- Real authentication/authorization, replacing the current placeholder user id.
- OCR/image support for scanned documents in the evidence pipeline.
- Infrastructure-as-code (CDK/Terraform/CloudFormation) for the AWS resources currently provisioned via one-off CLI commands, plus CI/CD for both deployments.
- A custom domain, ACM certificate, and Route 53 record for the CloudFront distribution.

## 25. License

[MIT](LICENSE).

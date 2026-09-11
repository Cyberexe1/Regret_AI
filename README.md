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
23. [REGRET ENGINE 2.0 — Decision Memory](#23-regret-engine-20--decision-memory)
24. [REGRET ENGINE 2.0 — Historical Decision Intelligence](#24-regret-engine-20--historical-decision-intelligence)
25. [REGRET ENGINE 2.0 — Value of Information](#25-regret-engine-20--value-of-information)
26. [REGRET ENGINE 2.0 — Adaptive Experiment Loop](#26-regret-engine-20--adaptive-experiment-loop)
27. [REGRET ENGINE 2.0 — Decision Evolution](#27-regret-engine-20--decision-evolution)
28. [REGRET ENGINE 2.0 — Cross-Decision Learning](#28-regret-engine-20--cross-decision-learning)
29. [Limitations](#29-limitations)
30. [Future improvements](#30-future-improvements)
31. [License](#31-license)

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

## 23. REGRET ENGINE 2.0 — Decision Memory

> "REGRET ENGINE doesn't just remember decisions. It remembers what was believed, what was tested, what actually happened, and what changed as a result."

**REGRET ENGINE 1.0:**

```
Decision → Analysis → Threshold → Experiment → Re-evaluation
```

**REGRET ENGINE 2.0:**

```
Decision → Analysis → Threshold → Experiment → Re-evaluation → Memory → Future Decisions
```

The 1.0 loop already produces a real, deterministic re-evaluation after every experiment result. 2.0 adds one capability on top of it: **Decision Memory** — a durable, structured record of what REGRET ENGINE has learned about a decision, distinct from the raw analysis records it's built from.

### What Decision Memory actually stores

- `DecisionMemory` (`backend/app/memory/memory_schemas.py`): a per-decision summary that *references* its critical assumptions/thresholds/regret scenarios/experiments by id — it never duplicates their content, which stays the single source of truth in `DecisionRepository`. Explicitly staged as `preliminary` (only the analysis exists — nothing is presented as an observed outcome) or `validated` (a real experiment result has been observed and re-evaluated).
- `MemoryLearning`: one durable, individually provenance-tracked fact per threshold comparison, assumption re-evaluation, or regret-scenario re-evaluation that a real re-evaluation actually produced — plus one for the experiment result's own submitted summary. Every learning's `source_type`/`source_id` points at the exact `ReEvaluation`/`ExperimentResult` record it came from.

### How memory is built — deterministically, never re-analyzed

Memory is a *consequence* of observed evidence, not a fourth agent call. Submitting an experiment result already triggers `ReEvaluationService`'s deterministic threshold comparison (see [Experiment + re-evaluation loop](#8-experiment--re-evaluation-loop)); `MemoryService` reads that already-computed result and turns it into learnings — no LLM call, no re-running the analysis pipeline:

```
POST /experiments/{experiment_id}/results
        ↓
persist result  →  deterministic re-evaluation  →  DecisionAssessment
        ↓
MemoryService.update_memory_from_reevaluation()
        ↓
MemoryLearning records (threshold_validated / threshold_failed / assumption_weakened / ...)
        ↓
DecisionMemory updated (stage: preliminary → validated)
        ↓
existing ExperimentResultResponse returned to the caller, unchanged
```

A memory-layer failure is logged and never fails the request — the experiment result and re-evaluation have already succeeded and must still be returned. Learning ids are derived deterministically from `(experiment_result_id, learning_type, discriminator)`, so re-processing the same result twice can never create duplicate learnings — a conditional DynamoDB write on that same, reproducible id is the idempotency guarantee, not a separate lock.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /decisions/{decision_id}/memory` | The memory summary, its learnings, the real experiments/re-evaluations it references, and its current unresolved uncertainties — one call. |
| `GET /decisions/{decision_id}/learnings` | Every learning ever recorded for a decision, oldest first. |
| `GET /memory/{memory_id}` | A single memory object by its own id. |

On the frontend, a decision's report page has a **Decision Memory** section (`DecisionMemoryPanel`) that makes the "what we thought" vs "what we learned" distinction visually explicit — the learned side stays visibly provisional (dashed border, "Not yet tested" badge) until a real experiment result exists — plus a timeline (`MemoryTimeline`) walking through Decision Created → Analysis Completed → Critical Threshold Identified → Experiment Started/Completed → Decision Re-evaluated → Learning Recorded. The dashboard's "Recent decision learnings" card surfaces a few of the workspace's most recent, real learnings.

### What this does not do (yet)

Decision Memory is a per-decision record. It does not compare decisions to each other, does not use one decision's memory to influence a different, future decision, and performs no semantic similarity search — that cross-decision capability was out of scope for Step 18. It is exactly what [Historical Decision Intelligence](#24-regret-engine-20--historical-decision-intelligence) below adds.

## 24. REGRET ENGINE 2.0 — Historical Decision Intelligence

> "A new decision can now discover relevant learning from the user's OWN previous decisions. Historical information is context, not truth."

**REGRET ENGINE 1.0:**

```
Decision → Failure Conditions → Threshold → Experiment → Re-evaluation
```

**REGRET ENGINE 2.0:**

```
Past Decisions → Memory → Historical Insight → New Decision → Failure Conditions → Threshold → Experiment → Re-evaluation → Updated Memory
```

Step 18 gave every decision a durable memory. This step ([`backend/app/memory/similarity.py`](backend/app/memory/similarity.py), [`backend/app/memory/historical_context.py`](backend/app/memory/historical_context.py)) makes that memory useful to the user's *next* decision — without a vector database, without embeddings, and without ever letting the past override the present.

### Decision Similarity — deterministic, explainable, never a black box

`DecisionSimilarityService` scores a new decision against the same user's own past decisions using a small, fixed set of named, independently-computed features — decision-text token overlap (Jaccard similarity over a lightweight, stopword-filtered tokenizer, not exact string matching and not an embedding model), assumption/key-variable overlap, budget closeness, and risk-tolerance/location matches. Every score's `matched_features` names exactly which components contributed, and `explanation` is a plain sentence built directly from them — never free-form LLM prose, and never a number a user or developer can't trace back to a concrete reason.

The result is a `SimilarityScore` with a `score` in `[0, 1]` — explicitly documented, in the schema itself, as a **historical relevance score**, not a probability and not a statistically calibrated measure of anything.

### Historical Insight retrieval — surfacing real learnings, never fabricating a pattern

`HistoricalContextService` orchestrates the rest, entirely in deterministic Python — no fourth agent, no LLM call:

```
DecisionRepository.list_for_user (bounded, user-scoped, existing GSI1 index)
        ↓
DecisionSimilarityService.rank (deterministic scoring, no vector DB)
        ↓
top HISTORICAL_TOP_K relevant past decisions
        ↓
MemoryRepository.list_learnings_for_decision (per relevant decision)
        ↓
HistoricalContext: relevant decisions, individual insights, recurring variables,
previously-failed assumptions, previously-validated thresholds, unresolved patterns
```

Every `HistoricalInsight` is copied verbatim from a real, already-persisted `MemoryLearning` (see [Decision Memory](#23-regret-engine-20--decision-memory)) — `source_decision_id`/`source_memory_id`/`learning_id` always point at the exact record it came from. Nothing is invented at this layer.

### User-scoping — the ownership boundary is explicit, not incidental

**A user's decision memory must never be returned to another user.** This is enforced at the service layer, not left to the API:

- The only way `HistoricalContextService` ever discovers candidate past decisions is `DecisionRepository.list_for_user(user_id, ...)`, which queries the existing GSI1 index keyed by `USER#<user_id>` — it is architecturally impossible for this query to return another user's decision, because the partition key itself is the user id.
- `get_historical_context`/`get_historical_context_preview` take `user_id` as a required, explicit parameter — never inferred, never defaulted.
- This is covered by a **mandatory** regression test: [`backend/tests/test_historical_context.py::test_user_a_cannot_retrieve_user_b_historical_context`](backend/tests/test_historical_context.py) seeds an essentially identical, fully-analyzed decision for two different users and asserts User A's historical context never surfaces User B's decision, memory, or learnings — even though the text would otherwise score very highly.

### The evidence hierarchy — historical context is background, never truth

Historical information is deliberately treated as the *lowest*-priority input into any analysis, explicitly ranked below the current decision's own evidence and constraints:

1. Current user-provided evidence
2. Current experiment observations
3. Deterministic calculations from current data
4. Explicit user constraints
5. Current analysis outputs
6. Historical validated learnings
7. Historical provisional learnings
8. General AI inference

`app/agents/decision_analyzer.py` renders historical context as its own, clearly-labeled section, appended *after* the current decision's own text and evidence, with an explicit instruction never to state a historical number as fact. Every individual insight is phrased as **"a previous decision observed X"**, never as a claim about the current decision — e.g. if a past decision's memory recorded a 17% repeat-order rate but the current decision's own evidence shows 31%, the prompt says "Previous decision observed 17%, but current evidence indicates 31%," never "Historical data proves the repeat-order rate is 17%."

Historical context is gathered as an additive step in `AnalysisOrchestrator`, before the Decision Analyzer runs — never a fourth agent call, and never able to block or fail the analysis: if gathering raises for any reason, the run proceeds exactly as if no history existed.

**Historical insights never automatically:** reject a decision, approve a decision, change a threshold, change an experiment result, change a user constraint, make a financial decision, or trigger an irreversible action. They surface information. The user remains the decision-maker.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /decisions/{decision_id}/historical-context` | The full `HistoricalContext` for an existing decision: relevant past decisions with their similarity scores, individual insights, recurring variables, previously-failed assumptions, previously-validated thresholds, and warnings. |
| `POST /decisions/historical-context/preview` | The same computation for a decision that hasn't been created yet — nothing is persisted — powering the intake-page preview below. |

The 9-stage analysis pipeline's own result also gains a `historical_context` key (see `AnalysisRun.result`) alongside every agent stage's output, recording what history was available when that specific run happened.

On the frontend: the **new-decision intake page** shows a live, debounced "Relevant from your past decisions" preview as the user types (never persisting anything); the **analysis workspace** has its own "Historical Insights" section once analysis completes; a decision's **report page** has a "Related past decisions" section explaining, in plain language, why REGRET connected each match; and the **dashboard** carries one small, bounded "Historical lessons" card (e.g. "3 validated learnings could apply to your recent decisions") rather than surfacing the full insight list everywhere.

### Configuration

Three bounded settings (mirroring the existing `research_max_*` bounding pattern) keep this a cheap, in-process computation regardless of how much decision history a user accumulates — see `backend/.env.example`:

| Variable | Default | Meaning |
|---|---|---|
| `HISTORICAL_SEARCH_LIMIT` | 20 | How many of the user's own most recent decisions are even considered as candidates. |
| `HISTORICAL_TOP_K` | 5 | How many of the highest-scoring candidates are kept as "relevant decisions". |
| `HISTORICAL_INSIGHT_LIMIT` | 10 | Upper bound on how many individual insights are ever surfaced at once. |

### What this does not do (yet)

No vector database, no embeddings, no semantic search — similarity is deterministic, lexical, and fully explainable. Value-of-Information prioritization now exists — see the next section. The Adaptive Experiment Loop that acts on a sequence of these rankings over time now exists too — see [Adaptive Experiment Loop](#26-regret-engine-20--adaptive-experiment-loop). Recurring patterns *across* a user's own decision history now exist too — see [Cross-Decision Learning](#28-regret-engine-20--cross-decision-learning). Learning shared *across* users remains out of scope. See [Future improvements](#30-future-improvements).

## 25. REGRET ENGINE 2.0 — Value of Information

> "REGRET ENGINE doesn't just ask what could make this decision fail. It asks which of those unknowns is actually worth spending effort to resolve before you commit."

**REGRET ENGINE 1.0 / early 2.0:**

```
Decision → Failure Conditions → Threshold → Experiment
```

**REGRET ENGINE 2.0 with Value of Information:**

```
Decision → Uncertainties → Potential Impact → Decision Sensitivity →
Current Evidence → Cost of Testing → Reversibility → Value of Information →
Priority → Experiment
```

Steps 18-19 gave REGRET ENGINE memory and the ability to compare a decision against a user's own history. This step ([`backend/app/services/value_of_information_service.py`](backend/app/services/value_of_information_service.py), [`backend/app/agents/value_of_information.py`](backend/app/agents/value_of_information.py)) answers a question none of the prior steps answer on their own: **of everything still uncertain about this decision, which uncertainty is most worth resolving first?**

### Risk is not the same thing as value to resolve

A common mistake decision tools make is conflating "how dangerous is this if wrong" with "how much should I spend effort finding out." REGRET ENGINE keeps these explicitly separate:

| Concept | Question it answers |
|---|---|
| **Risk / regret severity** | How bad would it be if this assumption turns out to be wrong? |
| **Uncertainty** | How much is genuinely unknown about this variable today? |
| **Impact** | How much would the decision's outcome change if this variable were wrong? |
| **Decision sensitivity** | If this variable changes even a little, how much does the decision's assessment move? |
| **Cost of learning** | What would it actually cost — money, time, reversibility — to find out? |
| **Value of Information** | Given all of the above, how much is it actually worth resolving this uncertainty *before* committing? |

A critical-impact assumption the decision is highly sensitive to, but that is already backed by strong evidence, has low remaining value to resolve — there's little left to learn. A moderate uncertainty that can be tested in a day for almost no cost can have *higher* practical value than a severe one that would take six months and significant capital to test. REGRET ENGINE's own regression suite pins this down explicitly: `test_high_risk_but_already_understood_scores_lower_than_genuinely_uncertain` and `test_low_cost_high_impact_outranks_high_cost_high_impact` in [`backend/tests/test_value_of_information_service.py`](backend/tests/test_value_of_information_service.py).

### The scoring methodology — documented, deterministic, never a fabricated statistic

No LLM call is involved anywhere in this feature. `DecisionSimilarityService`'s sibling here, `app/services/value_of_information_service.py`, computes everything from already-persisted, already-structured fields (`Assumption`, `Blindspot`, `Threshold`, `RegretScenario`, `Experiment`, and Step 19's `HistoricalContext`) using a fixed, documented formula (`methodology_version = "voi-v1"`):

1. **Information value** — three ordinal inputs (potential decision impact, decision sensitivity, current uncertainty level), each normalized into a small bounded range, multiplied together: `information_value_raw = impact × sensitivity × uncertainty`. It's a product, not an average, so information value can only be genuinely high when the decision is *both* sensitive to the variable *and* meaningfully uncertain about it *and* the downside if wrong is material — a well-understood variable caps the score low even if the impact would be severe. If any of the three inputs is unavailable, the result is `unknown`, never guessed.
2. **Practical value** — `information_value_raw` adjusted by real cost-to-test, feasibility, and reversibility multipliers, sourced only from an already-recommended `Experiment` that targets a related threshold (never fabricated for an uncertainty with no experiment). A cheap, feasible, reversible test barely discounts the score; an expensive, infeasible, irreversible one discounts it heavily.
3. **Bands, not fake precision** — both scores are bucketed into one of five interpretable bands (`very_low` / `low` / `medium` / `high` / `very_high`, or `unknown`) via fixed, documented cutoffs. The underlying raw float is never returned by the API or shown in the UI as if it were a calibrated probability.
4. **Ranking** sorts by practical value, tying on information value, then by a stable id — fully deterministic, same inputs always produce the same order.
5. **Historical relevance** (Step 19) is a **tiebreaker only** — it can decide between two uncertainties whose scores are nearly identical, but it can never reorder two uncertainties whose scores genuinely differ. Current evidence and the deterministic formula always outrank history, mirroring Step 19's own evidence hierarchy.

### Threshold and Experiment Planner integration — a hint, never an override

Every high-value uncertainty is connected to a real, persisted `Threshold` when one exists (`threshold_status: linked`); if none has been established yet, that's stated explicitly (`not_established`) rather than inventing one. The Value-of-Information analysis is computed as an additive step in `AnalysisOrchestrator`, right after thresholds are persisted and just before the Experiment Planner runs. The Experiment Planner receives the top-ranked uncertainty and its threshold (if any) as a clearly labeled **preference**, not a rule — its own system prompt (rule 13) explicitly allows it to target a different threshold if a cheaper or more reversible test serves the decision better. A Value-of-Information computation failure never blocks or fails the analysis run; the pipeline proceeds exactly as if it had never run.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /decisions/{decision_id}/value-of-information` | The most recently computed analysis: every ranked uncertainty, the primary one, its linked threshold (if any), and the rationale behind the ranking. |
| `POST /decisions/{decision_id}/value-of-information/recompute` | Recomputes from the decision's current state (e.g. after an experiment result changes the evidence) — creates a new analysis and marks the previous one superseded, but never deletes it, so the decision's full prioritization history stays reconstructable. |

Submitting a real experiment result (`POST /experiments/{id}/results`) automatically triggers a recompute — an uncertainty that was previously the top priority can drop once it's been tested, and a different one can become primary. Step 26 is what actually *acts* on that sequence of rankings over time.

On the frontend, a decision's report page has a **"What should you test first?"** section: a compact ranked bar list ("What matters most") for an at-a-glance read, followed by expandable cards for each uncertainty showing why it matters, its linked threshold, cost to learn, test duration, feasibility, and reversibility — with the top-ranked uncertainty visually marked "Test this first."

### What this does not do (yet)

Value of Information ranks uncertainties within one decision, at one point in time. On its own, it does not automatically re-run the ranking on a schedule or select the next experiment — it recommends what's worth finding out; the user remains the decision-maker. See the next section for the loop that carries that ranking forward across an entire testing journey.

## 26. REGRET ENGINE 2.0 — Adaptive Experiment Loop

> "REGRET ENGINE doesn't stop at one experiment. After a result comes in, it learns from it and asks: what's the next most valuable thing to find out?"

**Through Step 20:**

```
Decision → Uncertainties → Value of Information → Best Experiment → (done)
```

**REGRET ENGINE 2.0 with the Adaptive Experiment Loop:**

```
Decision → Uncertainties → Value of Information → Best Experiment →
Real-World Result → Re-evaluation → Updated Uncertainties →
Value of Information (recomputed) → Next Best Experiment → ... → Stop
```

Step 20 answers "what's worth testing right now?" This step ([`backend/app/adaptive/service.py`](backend/app/adaptive/service.py), [`backend/app/adaptive/schemas.py`](backend/app/adaptive/schemas.py), [`backend/app/adaptive/repository.py`](backend/app/adaptive/repository.py)) answers the question that only matters once a result actually comes back: **now what?** It closes the loop — Decision → Uncertainties → Value of Information → Best Experiment → Real Result → Re-evaluation → Updated Uncertainties → repeat — turning a single round of analysis into an ongoing validation journey.

### No new state machine over fabricated data — every field is derived from real records

`AdaptiveExperimentState` is the one new persisted entity this step adds, and it invents nothing: `current_assessment` is deterministically derived from the latest real `ReEvaluation`'s `decision_assessment` (status + confidence); each threshold's standing (`unknown` / `provisional` / `under_test` / `validated` / `failed` / `inconclusive`) is deterministically derived from real `ThresholdComparisonStatus` history; the next experiment is always a real, already-recommended `Experiment` selected from the freshest `ValueOfInformationAnalysis`'s own ranking — never a fabricated one. No LLM call happens anywhere in this feature; it is pure, deterministic Python reading data every prior step already produced.

### Why an experiment is never blindly repeated

The core rule (and the mandatory regression test, `test_after_resolving_uncertainty_a_selects_uncertainty_b_by_voi_rank` in [`backend/tests/test_adaptive_service.py`](backend/tests/test_adaptive_service.py)): once Uncertainty A's threshold reaches a conclusive state (`validated` or `failed`, from a real experiment result) or its experiment is `completed`, it is permanently skipped when selecting the next candidate — the loop walks the current VOI ranking in order and picks the highest-ranked uncertainty that hasn't already been conclusively tested. Re-testing something only happens if a later VOI recompute (reading the current, possibly-changed evidence) legitimately reopens it — this service never "reopens" a threshold on its own initiative.

### Knowing when to stop

The loop reaches a clearly labeled stopping state, never a silent "nothing happens," for any of these reasons:

| Status | Meaning |
|---|---|
| `sufficiently_validated` | Every uncertainty with meaningful practical value has already been conclusively tested, or what remains has low practical value relative to the effort to resolve it. |
| `inconclusive` | A worthwhile uncertainty remains, but no feasible (not-yet-run, not-cancelled) experiment exists for it. |
| `blocked` | No Value-of-Information analysis exists yet, or the decision has reached the configured maximum number of adaptive cycles (`max_adaptive_cycles`, default 8 — a hard ceiling against runaway looping, never an infinite test-forever machine). |
| `user_stopped` | The user explicitly stopped testing (`POST /decisions/{id}/adaptive/stop`) — the human always remains in control; REGRET ENGINE never decides on its own that testing is permanently "done" in a way the user can't override, and stopping never triggers any automatic action. |

### Idempotent and concurrency-safe by construction

`POST /decisions/{id}/adaptive/advance` computes the candidate next state and derives its id deterministically from `(decision_id, cycle_number, status, experiment_id, discriminator)` — the same inputs always produce the same id. Calling `advance` twice with no new evidence returns the *existing* state with `outcome: no_change` rather than creating a duplicate cycle, and two genuinely concurrent calls collide on the same DynamoDB item key, with a conditional write (`Attr("PK").not_exists()`) guaranteeing only one of them actually creates a new record. `cycle_number` only increments once a real result has actually been processed (`ready_for_next_experiment`) — re-advancing while still awaiting one result reuses the same cycle number instead of numbering phantom cycles.

### Deliberately deferred result-submission integration

`POST /experiments/{id}/results` calls `AdaptiveExperimentService.mark_experiment_completed`, which only marks the current cycle `ready_for_next_experiment` — it deliberately does **not** auto-select or start the next experiment inline. Picking what runs next always requires the separate, explicit `POST /decisions/{id}/adaptive/advance` call. This keeps "a result came in" and "here's what to test next" as two distinct, user-visible steps rather than one implicit side effect, and a failure in this bookkeeping (logged, never raised) can never block the result submission itself.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /decisions/{decision_id}/adaptive` | The current cycle: cycle number, validation status, the decision's current evidence-supported assessment (and the previous one, when it changed this cycle), the primary uncertainty/threshold/experiment being tracked, and what to do next. `404` if the loop hasn't started yet. |
| `GET /decisions/{decision_id}/adaptive/history` | Every cycle ever recorded for this decision, oldest first — append-only, so the full validation journey (Experiment 1 → Result → Learning → Experiment 2 → ...) stays reconstructable; nothing is ever deleted or overwritten. |
| `POST /decisions/{decision_id}/adaptive/advance` | Advances to the next logical state (idempotent — see above). |
| `POST /decisions/{decision_id}/adaptive/stop` | The user manually stops the loop; preserves all prior history. |

On the frontend, a decision's report page has a **"Decision validation"** section showing the current cycle and, when the assessment changed this cycle, the previous → current transition (e.g. "Supported → Weakened") rather than a vague "assessment updated," plus **"The next question"** — the next uncertainty/experiment and why, or a clear stopping banner once concluded — and a **validation history** timeline of every cycle the decision has gone through.

### What this does not do

The adaptive loop sequences experiments *within* one decision, one cycle at a time, and never on its own initiative: it never starts, runs, or submits results for an experiment automatically — a human always runs the real-world test and reports what happened. It does not learn across different users' decisions (see [Historical Decision Intelligence](#24-regret-engine-20--historical-decision-intelligence) for same-user history, which is as far as learning currently reaches), and it does not introduce any new infrastructure — `AdaptiveExperimentState` lives in the exact same single-table DynamoDB design as every other entity (`PK=DECISION#<id>`, `SK=ADAPTIVE_STATE#<state_id>`).

## 27. REGRET ENGINE 2.0 — Decision Evolution

> "REGRET ENGINE doesn't only show the final assessment. It preserves the journey — what we believed, what we tested, what we observed, what changed, what we learned, and what we test next."

Steps 18-21 each produce their own piece of a decision's history: memory (18), historical comparisons (19), a value-of-information ranking (20), and a sequence of adaptive cycles (21). None of them answer, in one place, the question a user actually asks after several rounds of testing: **"What changed my mind? Why did the system change its assessment? What evidence caused that change?"** This step ([`backend/app/evolution/service.py`](backend/app/evolution/service.py), [`backend/app/evolution/schemas.py`](backend/app/evolution/schemas.py), [`backend/app/evolution/repository.py`](backend/app/evolution/repository.py)) answers exactly that, by assembling the full causal chain:

```
WHAT WE BELIEVED → WHAT WE TESTED → WHAT WE OBSERVED →
WHAT CHANGED → WHAT WE LEARNED → WHAT WE TEST NEXT
```

### A view, never a second event database

The evolution timeline is not a new persisted entity. `backend/app/evolution/repository.py` holds no `create_*` method at all — it only reads from the repositories every prior step already built (`DecisionRepository`, `AnalysisRepository`, `EvidenceRepository`, `MemoryRepository`, `ValueOfInformationRepository`, `AdaptiveStateRepository`), and `DecisionEvolutionService` recomputes the ordered timeline from those real records on every request. There is nothing to keep in sync and nothing that can drift from the canonical data, because there is no copy of it — the timeline is a deterministic *view*, not a log a separate write path could get out of step with.

### Provenance, not a generic activity log

Every `DecisionEvolutionEvent` traces back to one specific canonical record via `source_type`/`source_id` (a real `Threshold`, `ExperimentResult`, `ReEvaluation`, `MemoryLearning`, or `AdaptiveExperimentState` id) — never a fabricated summary. `previous_state`/`new_state` are populated only when the source record itself carries a real before/after pair: a `ReEvaluation`'s own `previous_assessment`/`new_assessment`, or a threshold comparison's own met/missed outcome. An event like "Retention assumption weakened" is only ever emitted alongside its real trigger ("Experiment Result #X: observed repeat-order rate below threshold") and its real reason (the threshold comparison's own explanation) — REGRET ENGINE never states a causal claim ("the experiment proved customers disliked the product") that the underlying data doesn't itself support. Not every database write becomes an event, either: a re-evaluation that changed nothing produces no `assessment_changed`/`threshold_validated`/`threshold_failed` event, mirroring the same "only emit what actually changed" discipline the Adaptive Experiment Loop already applies to its own threshold-state bookkeeping.

### Decision Delta — "what changed?" as a structured comparison

`DecisionDelta` turns one event into a deterministic before/after comparison — which assumptions, thresholds, uncertainties, and experiments were affected, whether the overall assessment changed, and a plain-language explanation built only from those fields, never free-form prose. This is exposed both inline in the timeline (every state-changing event already carries its own previous/new state) and as its own endpoint for a specific event.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /decisions/{decision_id}/evolution` | The complete picture in one bounded call: current assessment, current cycle, the full (bounded) timeline oldest-first, a compact "major changes" list, current unresolved uncertainties, and validated/failed thresholds. Never one call per event — see the performance note below. |
| `GET /decisions/{decision_id}/evolution/{event_id}` | Full detail for one specific event. |
| `GET /decisions/{decision_id}/evolution/{event_id}/delta` | The structured `DecisionDelta` for that event. |

Bounded by `EVOLUTION_MAX_EVENTS` (default 200): a decision with a very long history keeps only its most recent events rather than loading an ever-growing, unbounded list — the response's own `truncated` flag says so explicitly rather than silently dropping history without telling the caller.

On the frontend, a decision's report page has a **"Decision Evolution"** section — deliberately not styled like a generic activity feed: a summary stats block (current assessment, cycles completed, uncertainties resolved/remaining, experiments completed), a vertical timeline with larger markers and an explicit "→" on every state-changing event, a compact **"Major Changes"** list (only events with real, meaningful impact — never every threshold/assumption record), and a closing **"Current State"** block that connects back to Step 21's adaptive loop. Clicking any timeline event opens a detail panel showing the reusable **`DecisionDeltaCard`** ("What changed?" — before/after/trigger/evidence) and, when the event references a real tested assumption, a **"What we believed" vs "What we learned"** block. Any historical insight surfaced from a *different* past decision (Step 19) is always labeled **HISTORICAL** and is never rendered as current evidence for this decision.

### Performance

The whole section renders from the single `GET .../evolution` call above — the frontend never issues one request per timeline event. Event-detail and decision-delta lookups only fire when a user actually opens a specific event's panel.

### What this does not do

Decision Evolution narrates what Steps 18-21 already decided and persisted — it contains no scoring, no ranking, and no cycle-selection logic of its own, and it never claims a causal relationship the source data doesn't establish. It is strictly per-decision; it does not compare or learn across a user's other decisions (that remains [Cross-Decision Learning](#28-regret-engine-20--cross-decision-learning)'s job, below), and it introduces no new infrastructure or database — the timeline is computed, never stored.

## 28. REGRET ENGINE 2.0 — Cross-Decision Learning

> "This system learns patterns only from the user's own historical decisions. It does not perform cross-user learning."

Step 19 ([Historical Decision Intelligence](#24-regret-engine-20--historical-decision-intelligence)) answers "which past decisions are relevant to *this* decision?" This step ([`backend/app/learning/`](backend/app/learning/)) answers a different question: **what keeps happening across *all* of a user's decisions?** A repeatedly-underperforming retention assumption, a threshold that keeps failing, an uncertainty that never gets tested, an experiment type that keeps paying off — patterns visible only when looking across a whole decision history, never from one decision alone.

```
Step 19:  Current Decision → "Which past decisions are similar?"
Step 28:  All Past Decisions → "What keeps recurring across them?"
```

### No generic AI-generated "insight" — every pattern is traceable

There is no LLM call anywhere in this feature. A `CrossDecisionPattern` is only ever created from real, already-persisted records — `DecisionMemory`, `MemoryLearning`, `ExperimentResult`, `ReEvaluation`, `Threshold` — via a `PatternOccurrence` provenance chain:

```
Pattern → Supporting decisions → Supporting learnings → Original experiment/re-evaluation evidence
```

Every pattern can always answer "why did REGRET learn this?" with real record ids (`GET /learning/patterns/{id}` returns every occurrence, its source type, and its source id) — never a fabricated citation.

### Deterministic normalization, never uncontrolled semantic clustering

Two decisions' observations are only ever grouped into the same pattern when their structured fields genuinely match after cleanup (lowercase, strip punctuation, drop a short stopword list, sort remaining tokens — see [`backend/app/learning/normalization.py`](backend/app/learning/normalization.py)) — never a semantic/embedding-based guess about what two differently-worded variables "probably mean." "Customer retention rate" and "repeat purchase behavior" are deliberately **not** merged unless a real, already-persisted link (e.g. both point at the same `Assumption.id`) says they should be — recognizing that kind of relationship without one is an explicit, documented limitation of this step, not a silent gap.

### Minimum evidence and pattern lifecycle

No pattern is ever created from a single decision. The deterministic policy:

| Independent supporting decisions | Result |
|---|---|
| 1 | No pattern at all |
| 2 | `emerging` / `repeated` |
| 3+, consistent | `established` |
| Contradicting evidence outweighs support | `confidence` lowered, status moves toward `contradicted` |

These are heuristics, never a statistical significance test — nothing in this feature computes or displays a p-value, a confidence interval, or a fabricated percentage ("87% likely"). `confidence` is one of three qualitative bands (`low`/`medium`/`high`), weighted toward **observed** evidence (real experiment results, re-evaluations) over speculative analysis-time assumptions alone — see the evidence hierarchy below. A pattern that becomes `inactive` (no supporting evidence remains after a refresh) is never deleted; its full history stays queryable, per the "preserve provenance" principle carried through every REGRET ENGINE 2.0 step.

### Conflict handling — mixed evidence is shown as mixed

Three decisions where an assumption was validated twice and failed once never collapse into "this assumption always holds." The dominant direction (2 vs 1) becomes the pattern, but the contradicting decision is recorded and surfaced alongside it (`contradicting_decision_ids`, plus a `contradicted` status and lowered confidence when contradictions are strong enough) — see spec's own example: "Retention outcomes have been mixed across your past decisions," never "Retention assumptions fail."

### Evidence hierarchy — cross-decision learning is context, never authority

1. Observed experiment results
2. Re-evaluation outcomes
3. Validated/failed thresholds
4. Explicit memory learnings
5. Historical analysis
6. Similarity/inference

A recurring pattern from a user's history can **never** override the current decision's own evidence, a real threshold, or a deterministic calculation. This is enforced structurally, not by convention: `historical_learning_signal` (see below) is applied to a Value-of-Information ranking strictly as a tiebreaker-strength enrichment *after* the deterministic VOI formula has already ranked every uncertainty — it can never change `practical_value` or reorder the ranking itself.

### User isolation — absolute, structural, and tested

Every pattern lives under `PK=USER#<user_id>` in the existing single-table DynamoDB design (no new table, no vector DB, no Redis, no PostgreSQL) — the partition key itself *is* the user id, so a query for one user's patterns cannot structurally return another's. `PatternOccurrence` rows live in the same user partition. Every repository method requires `user_id`; there is no method anywhere in [`backend/app/learning/repository.py`](backend/app/learning/repository.py) that lists patterns without one. Dedicated tests (`test_learning_repository.py`, `test_learning_service.py`) confirm User A can never retrieve, or even accidentally collide with, User B's patterns or occurrences — including the case where both users' deterministic pattern ids happen to be identical.

### Integration with Value of Information and the Experiment Planner

When a recurring pattern names the same variable as an uncertainty in a fresh VOI ranking, that item's `historical_learning_signal` (`none`/`weak`/`moderate`/`strong`) and a plain-language `historical_learning_explanation` are attached — a failed/underperforming or recurring-unresolved pattern raises the signal (worth testing early); a validated/successful pattern lowers it (already well understood). The Experiment Planner receives this the same way it already receives the Step 20 VOI hint — as rule 14 in its own system prompt, a strong preference it may still override, and it is explicitly instructed never to recommend an experiment *solely* because a pattern was common historically; it must still target a real, current threshold.

### Refresh is explicit, never automatic on every read

`GET /learning/patterns`, `GET /learning/patterns/{id}`, and `GET /decisions/{id}/patterns` only ever return whatever the last refresh computed — they never trigger detection themselves. `POST /learning/patterns/refresh` is the one operation that (re)computes patterns, idempotently (a deterministic `pattern_id`/`occurrence_id` means re-running with no new evidence reports `patterns_unchanged`, never a duplicate), and bounded to the user's own most recent `LEARNING_MAX_DECISIONS_SCANNED` decisions (default 50) so it never scans an unbounded history.

### Where it's exposed

| Endpoint | Returns |
|---|---|
| `GET /learning/patterns` | Every pattern for the caller's own decisions, with optional `pattern_type`/`status`/`domain`/`variable` filters. |
| `GET /learning/patterns/{pattern_id}` | One pattern's full detail: every occurrence, and the supporting/contradicting split. |
| `GET /decisions/{decision_id}/patterns` | Patterns that name this specific decision as supporting or contradicting evidence. |
| `POST /learning/patterns/refresh` | Rebuilds the caller's own patterns from their current canonical records. Idempotent. |

On the frontend: a **"Patterns across your decisions"** card on the dashboard, a **"What your past decisions teach"** section on the decision report page (only shown once a real pattern names that decision), and a **"Relevant learnings from your history"** section during new-decision intake — all deliberately kept visually behind whatever current evidence the page is already showing.

### What this does not do

No vector database, no embeddings, no semantic search infrastructure, no global or cross-user learning, no platform-wide behavioral profiles, and no new agents. This system learns patterns only from the user's own historical decisions — never another user's, and never a shared statistic computed across users.

## 29. Limitations

- AI-generated analysis (assumptions, blindspots, challenges, regret scenarios, thresholds, experiments) can be wrong or incomplete — it reflects what the model inferred from what it was given, not ground truth.
- A threshold can remain `provisional` or qualitative (no numeric value) when the available evidence doesn't support deriving a specific number — the system never fabricates one to look more concrete.
- The Experiment Planner can legitimately recommend zero experiments if it judges that nothing in the analysis justifies a well-designed test yet, rather than inventing generic advice ("talk to customers") to fill the slot.
- External research quality (when enabled) depends entirely on what the provider's search actually returns — it can find nothing relevant, and the system reports that honestly rather than filling the gap.
- Experiment recommendations and re-evaluations are decision-support, never guarantees — REGRET ENGINE does not, and is explicitly designed not to, make an irreversible decision automatically on the user's behalf.
- Evidence storage currently uses the container's local disk, not Amazon S3, even though an S3 bucket is provisioned for it — the `StorageBackend` interface supports adding an S3 implementation later without changing any calling code, but that implementation doesn't exist yet.
- There is no authentication yet; every request is attributed to a single placeholder user id. The data model and every access pattern are already user-scoped so real auth can be added later without rewriting routes.
- `/analyze` is currently synchronous — the HTTP request blocks until the full ~9-stage pipeline finishes (with generous timeouts and an idempotency guard against duplicate runs), rather than a submit-and-poll background job model.
- Cross-Decision Learning's normalization (see [Cross-Decision Learning](#28-regret-engine-20--cross-decision-learning)) only groups two decisions' observations together when their structured fields genuinely match after cleanup — it will not recognize that "customer retention" and "repeat purchase behavior" describe a related concept unless a real structured link (e.g. a shared `Assumption.id`) already connects them. This is a deliberate, documented limitation, not a bug: the alternative (semantic/embedding-based clustering) was explicitly out of scope for this step.

## 30. Future improvements

- An S3-backed `StorageBackend` implementation for evidence, behind the interface that already exists.
- Move `/analyze` to a genuinely asynchronous, submit-and-poll execution model now that the pipeline has grown to ~9 sequential stages.
- Real authentication/authorization, replacing the current placeholder user id.
- OCR/image support for scanned documents in the evidence pipeline.
- Infrastructure-as-code (CDK/Terraform/CloudFormation) for the AWS resources currently provisioned via one-off CLI commands, plus CI/CD for both deployments.
- A custom domain, ACM certificate, and Route 53 record for the CloudFront distribution.
- Cross-User Learning — deliberately out of scope. Value-of-Information prioritization (see [Value of Information](#25-regret-engine-20--value-of-information)), the Adaptive Experiment Loop that acts on it over time (see [Adaptive Experiment Loop](#26-regret-engine-20--adaptive-experiment-loop)), the Decision Evolution timeline that narrates the result (see [Decision Evolution](#27-regret-engine-20--decision-evolution)), and Cross-Decision Learning across a single user's own history (see [Cross-Decision Learning](#28-regret-engine-20--cross-decision-learning)) now exist; learning shared *across* users does not, and is not planned — every step above is explicitly, structurally scoped to one user's own decisions.
- Semantic/embedding-based similarity for historical retrieval and pattern normalization, as a richer alternative to today's deterministic, lexical-overlap scoring, should a real need for it emerge.
- Optional, strictly-bounded LLM-assisted normalization for Cross-Decision Learning (e.g. recognizing that two differently-worded variables describe the same underlying concept) — deliberately deferred; deterministic structured matching is the only method implemented today.

## 31. License

[MIT](LICENSE).

# REGRET ENGINE

**Tagline:** Know what could make your decision fail.

**Track:** Agents for Humans — decision-support / personal & small-business decision intelligence. REGRET ENGINE is a multi-agent system that helps a person validate a real decision before committing to it, which is the category this submission fits, based on the product as actually implemented (not a chatbot/assistant track, and not a pure data-analytics track — the product's entire value proposition is agentic reasoning applied to one person's specific, uncertain decision).

---

## Inspiration

People generally don't need another AI opinion. They already have friends, forums, and a dozen chat assistants willing to tell them what to do. What's actually missing is much narrower and much more useful: an honest answer to two specific questions —

> "What would have to be true for this decision to work?"

and

> "What should I test before I commit?"

Most decisions that go badly don't fail because the underlying idea was bad. They fail because nobody identified the one variable that actually mattered until the money was already spent. REGRET ENGINE exists to surface that variable *before* the commitment, not after.

## What it does

A user describes a real decision they're facing — in their own words, with real constraints (budget, timeline, location, risk tolerance) and, optionally, real evidence they've already gathered (a pilot week's sales data, a supplier quote, a lease document). REGRET ENGINE runs that decision through a nine-stage agent pipeline on Amazon Bedrock and returns a structured decision report: the assumptions the decision depends on, the blindspots nobody asked about, what the actual evidence supports or contradicts, the strongest counter-argument against it, the specific ways it could go wrong, and — the center of the product — the exact threshold (a variable and a tipping-point value) that separates "this works" from "this fails." It then recommends the cheapest real-world experiment that would tell the user whether that threshold is likely to be met. Once the user runs that experiment and reports what actually happened, REGRET ENGINE deterministically re-evaluates the decision against the real result and produces an updated assessment.

## How it works

Nine sequential, specialized agents, each a real `strands.Agent` on Amazon Bedrock, each consuming only the already-persisted structured output of the agents before it:

```
Decision Analyzer → Assumption Hunter → Blindspot Hunter → Research Agent (optional)
→ Evidence Agent → Devil's Advocate → Regret Simulator → Threshold Engine → Experiment Planner
```

The orchestrator (`backend/app/agents/orchestrator.py`) is the only thing that ever invokes an agent, persists its structured Pydantic output, and moves to the next stage. When the user later submits an experiment result, a *deterministic* re-evaluation service — not another model call — compares the observed value against the real threshold and produces the updated assessment. Full pipeline and diagrams: [`docs/agent-workflow.md`](docs/agent-workflow.md) and [`docs/architecture.md`](docs/architecture.md).

## What makes it different

The differentiation isn't "we use multiple agents." It's the specific artifacts the pipeline is built to produce, none of which a single-turn AI opinion produces on its own:

- **Failure conditions**, not risk scores — a specific `RegretScenario` describing exactly how the decision would go wrong, not a vague "this seems risky."
- **A decision-breaking threshold** — the Threshold Engine's entire job is naming the one variable and tipping-point value that actually determines success or failure, and it's allowed to say "provisional" or leave it qualitative rather than inventing a number the evidence doesn't support.
- **Evidence grounding** — the Evidence Agent is instructed to mark a claim `insufficient` rather than treat silence in the evidence as support; every reference to a specific piece of evidence, assumption, or blindspot is checked against real, already-persisted ids before persistence — a model-invented id is dropped, never stored.
- **The cheapest credible validation experiment** — not "do more research" (explicitly forbidden as a recommendation), but a concrete, low-commitment test with observable success/failure criteria tied directly to the real threshold.
- **Re-evaluation after real results** — the loop doesn't end at the report. A user can run the experiment, submit what actually happened, and get back a deterministic (not re-guessed) updated assessment: `strengthened`, `weakened`, `unchanged`, `inconclusive`, or `requires_more_evidence`.

## Technical Implementation

- **Frontend:** React 19 + TypeScript, Vite, React Router, TanStack-style data hooks, Tailwind CSS, Recharts, @xyflow/react (dependency graph visualization).
- **Backend:** FastAPI (Python 3.12), Pydantic v2, boto3.
- **AI orchestration:** [Strands Agents SDK](https://strandsagents.com/) (`strands-agents` on PyPI) — every pipeline stage is a real `strands.Agent` with a `structured_output_model`.
- **Model provider:** Amazon Bedrock, Amazon Nova Pro via the cross-region inference profile `apac.amazon.nova-pro-v1:0`.
- **Persistence:** Amazon DynamoDB, single-table design.
- **Storage:** Amazon S3 (a dedicated, private evidence bucket is provisioned and IAM-permissioned; the active storage backend today is local disk inside the container — see the main [README's Limitations section](README.md#26-limitations)).
- **Compute:** AWS App Runner (containerized FastAPI, pulling from a private Amazon ECR repository, IAM instance role, no AWS access keys).
- **Frontend hosting:** Amazon CloudFront in front of a private Amazon S3 bucket (Origin Access Control).
- **External research (optional):** a built-in DuckDuckGo HTML-search provider, no API key required, disabled by default (`RESEARCH_PROVIDER=none`).

No other AWS service, database, or external API is used. Nothing above was claimed without being present in the repository.

## AWS Usage

| Service | Role in this project |
|---|---|
| **Amazon Bedrock** | Runs all nine agent stages via the Strands Agents SDK. |
| **AWS App Runner** | Hosts the backend container; the only component with an AWS IAM identity. |
| **Amazon DynamoDB** | Stores every decision and every agent's structured output, single-table design with two GSIs. |
| **Amazon S3** | Two separate, fully private buckets — one for the frontend's static build (served via CloudFront), one reserved for evidence storage. |
| **Amazon CloudFront** | Public HTTPS entry point for the frontend, backed by S3 via Origin Access Control. |
| **Amazon ECR** | Private, scanned, immutable-tag registry for the backend's Docker image. |
| **AWS IAM** | Two least-privilege roles (App Runner instance role, App Runner ECR-access role) — no wildcard permissions, no `AdministratorAccess`. |

## Challenges

- **Cross-region Bedrock inference profiles.** Amazon Nova Pro isn't invocable by its raw foundation-model id alone; it required discovering and using the cross-region inference profile id, and — for least-privilege IAM — authorizing both the inference-profile ARN *and* all six underlying per-region foundation-model ARNs it can route to.
- **A transient Bedrock streaming error.** Real production runs occasionally hit `modelStreamErrorException` mid-stream (a provider-side transient failure, not a prompt or code bug). Root-caused it to `botocore.exceptions.EventStreamError` and added a narrow, capped retry around every Bedrock call site — retrying only that specific transient error class, never masking a genuine failure.
- **Keeping nine sequential agents honest about grounding.** Every agent's system prompt and the orchestrator's own id-cross-checking (dropping any reference to an id the model wasn't actually given) exist specifically to stop the pipeline from fabricating a link between claims that were never actually connected.
- **Immutable ECR tags.** The container registry was deliberately configured with `imageTagMutability=IMMUTABLE` for auditability, which meant every redeploy needed a fresh, unique image tag rather than overwriting `:latest` — a small but real operational constraint discovered mid-project.
- **CloudFront + client-side routing.** Serving a React Router SPA from a private S3 origin required explicitly configuring CloudFront's custom error responses (403/404 → `/index.html`) so a direct load or refresh on a deep route like `/decision/:id/analysis` doesn't return a raw S3 404.

## Impact

Anyone facing a real, uncertain, moderately costly decision — starting a small business, taking a job, signing a lease, making a personal investment — currently has two realistic options: guess, or ask an AI that will confidently produce an opinion regardless of how thin the underlying evidence actually is. REGRET ENGINE targets the gap between those two options: it doesn't remove the uncertainty, but it makes the uncertainty specific, falsifiable, and cheap to test before the real commitment happens.

## Future Scope

- An S3-backed evidence storage implementation, behind the interface that already exists for it.
- A genuinely asynchronous `/analyze` execution model (submit-and-poll) now that the pipeline has grown to ~9 sequential stages.
- Real user authentication, replacing the current single placeholder user id.
- OCR/image support for scanned evidence documents.
- Infrastructure-as-code and CI/CD for the AWS resources currently provisioned via one-off CLI commands.

## Demo

**LIVE DEMO URL:** [https://d20l6vg17brb6a.cloudfront.net]

**SOURCE CODE:** [ADD PUBLIC REPOSITORY URL]

**VIDEO:** [ADD YOUTUBE/VIMEO URL]

See [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) for the full demo walkthrough and [`docs/DEMO_DATA.md`](docs/DEMO_DATA.md) for the exact demo data used to reproduce it.

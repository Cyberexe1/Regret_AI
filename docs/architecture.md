# REGRET ENGINE — System Architecture

This is the actual, deployed infrastructure architecture — not an aspirational diagram. Every component below is real, running, and documented in detail in [`backend/README.md`](../backend/README.md).

## Diagram

```mermaid
flowchart TD
    User(["User's browser"])

    subgraph client["CLIENT (browser)"]
        CF["Amazon CloudFront<br/>(public HTTPS entry point)"]
        React["React + TypeScript SPA<br/>(static build, served from a<br/>private S3 bucket via CloudFront OAC)"]
    end

    subgraph backend["APPLICATION BACKEND (AWS App Runner)"]
        AppRunner["AWS App Runner<br/>(runs the container, IAM instance role,<br/>no AWS access keys)"]
        FastAPI["FastAPI<br/>(app/main.py, versioned /api/v1 routes)"]
    end

    subgraph orchestration["AI ORCHESTRATION"]
        Strands["Strands Agents SDK<br/>(AnalysisOrchestrator, 9-stage pipeline)"]
        Bedrock["Amazon Bedrock<br/>(Amazon Nova Pro,<br/>cross-region inference profile)"]
    end

    subgraph storage["PERSISTENT STORAGE (AWS managed)"]
        DynamoDB["Amazon DynamoDB<br/>(single table: decisions, agent<br/>results, analysis runs)"]
        S3Evidence["Amazon S3<br/>(evidence bucket, private,<br/>reserved for future S3 storage backend)"]
    end

    subgraph external["EXTERNAL SERVICES (optional)"]
        Research["Research Agent<br/>DuckDuckGo HTML search<br/>(RESEARCH_PROVIDER=http, off by default)"]
    end

    User -->|HTTPS| CF
    CF -->|serves static assets| React
    React -->|HTTPS fetch, VITE_API_BASE_URL<br/>ONLY this call ever leaves the browser| AppRunner
    AppRunner --> FastAPI
    FastAPI -->|invokes agents via orchestrator| Strands
    Strands -->|structured Pydantic I/O| Bedrock
    Strands -.->|optional external evidence,<br/>never blocks the pipeline| Research
    FastAPI -->|persists decisions,<br/>agent results, run status| DynamoDB
    FastAPI -->|evidence file storage<br/>bucket provisioned, not yet wired up| S3Evidence
```

(Mermaid source: [`architecture.mmd`](architecture.mmd).)

## Reading the diagram in 20 seconds

1. **Client**: CloudFront serves the React SPA. The browser talks to nothing else in AWS — ever.
2. **Application backend**: App Runner hosts FastAPI in a container. This is the *only* thing with an AWS identity (an IAM instance role, no access keys).
3. **AI orchestration**: FastAPI calls the Strands Agents SDK, which runs 9 sequential agents on Amazon Bedrock.
4. **Persistent storage**: DynamoDB holds every decision and every agent's structured output. An S3 bucket exists for evidence, provisioned and IAM-permissioned, but not yet the active storage backend (see [Limitations](../README.md#26-limitations)).
5. **External services**: an optional Research Agent can search the open web (DuckDuckGo) for additional context — off by default, and never merged into user-uploaded evidence.

## Boundary notes

- **Browser/client boundary**: the React app is static, unauthenticated content served by CloudFront from a *private* S3 bucket (Origin Access Control — direct S3 access returns `403`). The only network call the browser ever makes outside of loading its own static assets is `fetch()` to the FastAPI backend's public HTTPS URL.
- **AWS managed services**: CloudFront, App Runner, DynamoDB, S3, Bedrock, and ECR (not pictured — it's the private container registry App Runner pulls its image from) are all AWS-managed; nothing here is self-hosted infrastructure.
- **Application backend**: a single FastAPI process, containerized, with no in-process state beyond a process-wide concurrency guard for analysis runs. All real state lives in DynamoDB.
- **AI orchestration**: the Strands Agents SDK and Amazon Bedrock are only ever invoked by `AnalysisOrchestrator` (`backend/app/agents/orchestrator.py`) — never directly from an HTTP route handler.
- **Persistent storage**: DynamoDB is single-table (see the key schema in `backend/README.md`); S3 is used today only for the frontend's static build via CloudFront (a *separate* bucket from the evidence bucket).
- **External services**: the only third-party network call in the whole system is the optional Research Agent's outbound HTTPS request to a public search endpoint — no API key required, strictly bounded (max queries/results/timeout), and disabled by default.

## Security-relevant facts this diagram encodes

- The browser never calls DynamoDB, S3, or Bedrock directly.
- No AWS access keys exist in the React build, the Docker image, or App Runner's environment variables — App Runner's instance role is the only credential path, resolved automatically by boto3/Strands.
- Both S3 buckets (frontend, evidence) have Block Public Access fully enabled.
- The App Runner instance role is scoped to exactly the DynamoDB table + indexes, the evidence bucket, and the specific Bedrock inference profile/model — never a wildcard.

See [`docs/agent-workflow.md`](agent-workflow.md) for the reasoning pipeline itself, kept as a separate diagram from this infrastructure view.

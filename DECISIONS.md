# Design Decisions & Rationale

## Architecture Overview
The application is structured as a synchronous, decoupled Django REST Framework (DRF) backend that acts as an orchestrator for an autonomous LLM research agent. When a client triggers a research request, the backend coordinates a centralized "Research Loop" inside `engine.py`. The agent utilizes Gemini's native function-calling API to map specific technical targets to a set of predefined internal tools (`list_github_files`, `read_github_file`).

### The Synchronous Choice
A foundational architectural decision was made to execute the agent's logic entirely inside a **Synchronous Architecture**. In production LLM systems, long-running workflows are usually offloaded to asynchronous task workers (e.g., Celery with Redis) and real-time frontend updates are streamed via WebSockets or Server-Sent Events (SSE). 

However, for the specific requirements of this implementation, a synchronous architecture was chosen to maximize structural transparency, deterministic tracing, and raw readability. By keeping the execution thread within the HTTP lifecycle, we keep the codebase clean of infrastructure-heavy message brokers, ensuring the core mechanics of the agent's loop remain the absolute focal point.

---

## Database Schema Rationale
The persistence tier is modeled using an explicit, normalized relational structure consisting of three primary entities: `Repository`, `ResearchSession`, and `Finding`. 

1. **`Repository`**: Houses static codebase tracking information, ensuring metadata isn't duplicated across identical research paths.
2. **`ResearchSession`**: Aggregates the root query, the synthesized response text, and the structural metrics (token usage).
3. **`Finding`**: Acts as an immutable transaction log of an individual tool execution or internal step taken by the agent during the loop.

### Scaling & Trade-offs
This highly normalized approach is optimal for verification and inspection. Because every tool execution is recorded as a discrete row linked to a session, debugging hallucinations or loop drift is simple. 

However, at production scale, this model creates a significant database write bottleneck. High-velocity autonomous agents executing dozens of fast-paced tool queries can cause write amplification on transactional relational tables. If this platform scaled to process millions of concurrent queries, the sensible transition would be to denormalize the `Finding` entity entirely, converting it into a structured `JSONB` column directly embedded inside the `ResearchSession` table, or moving the transaction logs to a high-throughput NoSQL document repository (like MongoDB).

---

## Key Design Decisions & Trade-offs
* **Signals Over Heavy Monitoring Platforms (Sentry):** Rather than integrating third-party monitoring suites or error reporting platforms, the system uses native Django lifecycle signals (`post_save`) coupled with standard Python `logging`. This design cleanly decouples database persistence from logging side effects without complicating the environment setup with token management, external dashboards, or third-party SDK dependencies.
* **Native CI/CD Over Black-Box AI Reviewers:** Instead of piping PR reviews through automated third-party SaaS platforms like CodeRabbit, energy was focused on constructing a highly reliable, containerized CI/CD testing pipeline using GitHub Actions, Docker, and `pytest`. This prioritizes concrete code quality control via isolated, repeatable unit/integration tests over speculative AI reviews.
* **Deterministic Loop Constraints:** To remove the inherent risk of autonomous agents entering recursive infinite loops—which can rapidly deplete token quotas and cause thread lockup—the implementation introduces a hard boundary condition (maximum iteration limit). If the agent fails to reach a terminal response state within the capped limits, it is systematically halted and forced to synthesize an output using the context gathered up to that point.

---

## What I'd Do Differently With More Time
If granted an extended engineering window, the project would be refactored to include:
1. **Asynchronous Execution States:** Transitioning the blocking execution flow into an asynchronous worker queue (Celery) and returning an instant `202 Accepted` status with a tracking task ID.
2. **Vector Space Ingestion (RAG Architecture):** Rather than relying on live, recurring GitHub API calls to fetch raw text data over network barriers, the repository would be cloned locally on creation, parsed into an Abstract Syntax Tree (AST), broken into contextual chunks, and indexed into a local vector extension (like `pgvector`). This would dramatically minimize latency and slash context window consumption.

---

## AI Tools Usage
AI-assisted coding suites (such as Cursor and Copilot) were leveraged throughout development to streamline structural configuration and accelerate boilerplate setup.

* **What Worked Well:** AI was highly productive at scaffolding standardized Django REST Framework models, setting up configuration parameters inside multi-container `docker-compose.yml` structures, and generating boilerplate test data structures using `factory_boy`.
* **What Didn't Work:** The AI struggled with context-dependent application configurations and internal Django pathing mechanics. For instance, it failed to resolve implicit application namespace errors during test route matching (`NoReverseMatch` exceptions for `apps.soyoe`), frequently proposing redundant settings changes instead of target string alignment.
* **What Was Handled Manually:** The engineering of the central execution loop, setting up the custom Python tracking logs, structuring complex transactional testing assertions (such as `caplog` testing for signal firing), and writing the strict Docker validation layers inside the GitHub Actions YAML files were executed entirely by hand.

---

## Limitations & Known Issues
* **Gateway Timeouts:** Because the system runs fully synchronously, an evaluation request targeting a deeply nested repository with multiple dependencies may exceed the standard HTTP timeout limits before completing its research.
* **Context Overrun Vulnerability:** The engine lacks an inline token truncation mechanism for large single files. If the agent reads a file exceeding the maximum context space, the Gemini engine will reject the payload.
* **GitHub Rate Capping:** Remote repo analysis relies on unauthenticated GitHub API endpoints, leaving the application highly vulnerable to rate-limiting blocks during concurrent sessions.
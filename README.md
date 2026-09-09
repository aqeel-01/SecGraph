# SecGraph

## Introduction

SecGraph is an AI-powered API security reviewer for Python backend projects.
It helps developers find security weaknesses while they are building and
reviewing APIs, without requiring them to manually inspect an entire
repository.

SecGraph combines deterministic static analysis with optional local or cloud AI
explanations. It understands backend structure through Python AST indexing,
FastAPI route detection, code relationships, and incremental file hashing. It
can analyze a ZIP upload, a connected GitHub repository, or changed backend
code in a pull request.

## Problem statement

API security issues are often discovered too late or spread across too many
tools:

- Developers must manually inspect routes, authentication dependencies, data
  access, and input handling.
- Traditional scanners produce isolated pattern matches without understanding
  how functions and routes are connected.
- Full-repository scans are slow and repeatedly analyze unchanged code.
- AI tools may receive too much source code, increasing cost and privacy risk.
- Pull-request reviews rarely provide focused security feedback on changed
  backend code.

The goal of SecGraph is to provide a focused security review workflow that
connects API routes to the code behind them, highlights likely security
problems, explains findings using only relevant context, and avoids unnecessary
reprocessing.

## What SecGraph solves

SecGraph provides one workflow for:

1. Uploading or connecting a Python backend project.
2. Discovering relevant source files and backend frameworks.
3. Indexing the project structure and relationships.
4. Running deterministic security rules.
5. Reusing unchanged analysis through SHA-256 hashes.
6. Sending compact, relevant context to Ollama or Groq when AI adds value.
7. Displaying findings, evidence, impact, and remediation in a dashboard.
8. Reviewing changed backend code in GitHub pull requests.

## Features

- Secure ZIP project upload with path-traversal and archive-size protection.
- Recursive Python backend discovery.
- FastAPI framework and route detection.
- SHA-256 file tracking for incremental scans.
- Python AST indexing for imports, classes, functions, calls, decorators, and
  assignments.
- Relational code graph with `CALLS`, `IMPORTS`, and `ROUTES_TO` relationships.
- Deterministic rules for authentication, IDOR, SQL injection, secrets,
  sensitive data, and rate limiting.
- Compact AI context containing only relevant source and relationships.
- Ollama and Groq provider support with one-variable switching.
- GitHub repository import and signed pull-request webhook analysis.
- Celery and Redis background scan processing.
- Next.js dashboard for projects, scans, findings, and security summaries.

## Analysis pipeline

```text
Project ZIP / GitHub repository
              |
              v
Secure storage and preprocessing
              |
              v
Python files, hashes, framework and route detection
              |
              v
AST index and relational code graph
              |
              v
Deterministic security rules
              |
              v
Relevant security context
              |
              +── static finding only
              |
              +── Ollama or Groq explanation
              |
              v
Persisted finding and dashboard/PR result
```

For later scans, unchanged files are reused. Added, modified, deleted, and
dependent files are identified from stored hashes and import relationships.

## Architecture

```text
Next.js frontend
        |
        v
FastAPI API ─── PostgreSQL
        |
        +── Redis ─── Celery worker
        |                 |
        |                 +── preprocessing
        |                 +── AST indexing
        |                 +── code graph
        |                 +── static rules
        |                 +── AI explanation
        |
        +── Ollama or Groq
```

## Requirements

For local development:

- Python 3.11+
- Node.js 20+
- PostgreSQL 16 is recommended
- Redis 6+
- Ollama, if using local AI

Docker Desktop can provide PostgreSQL and Redis.

## Quick start with Docker

From the repository root:

```powershell
docker compose up --build
```

Services:

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API documentation: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- PostgreSQL: localhost:5432
- Redis: localhost:6379

Stop services:

```powershell
docker compose down
```

The Compose development profile disables API-key authentication. Do not expose
that profile directly to the public internet.

## Backend local setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Run the Celery worker in another terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
celery -A app.services.scan_tasks.celery_app worker --loglevel=INFO -P solo
```

The local backend `.env` is ignored by Git. It contains the AI provider choice,
database connection, Redis URL, and optional secrets.

## AI provider selection

Edit only `backend/.env`:

```env
AI_PROVIDER=ollama
```

Available values:

```env
AI_PROVIDER=ollama
AI_PROVIDER=groq
AI_PROVIDER=auto
```

- `ollama`: use local Ollama models.
- `groq`: use Groq for eligible AI analysis.
- `auto`: use the legacy routing policy.

High-confidence findings can be controlled independently:

```env
AI_SKIP_HIGH_CONFIDENCE=true
AI_STATIC_CONFIDENCE_THRESHOLD=0.85
```

With `true`, findings at or above the threshold skip AI. Set it to `false` to
send those findings to the selected provider as well.

For Ollama:

```powershell
ollama pull deepseek-r1:1.5b
ollama pull deepseek-r1:7b
```

For Groq, set the key once:

```env
AI_PROVIDER=groq
GROQ_API_KEY=your_key_here
GROQ_MODEL=deepseek-r1:7b
```

Restart the API and Celery worker after changing `.env`. High-confidence
deterministic findings may intentionally skip AI analysis.

## Frontend local setup

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend uses:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/api
```

If production API authentication is enabled, configure
`NEXT_PUBLIC_API_KEY` for the frontend client.

## Project workflow

### Upload a ZIP project

Use the dashboard upload page or:

```text
POST /api/projects/upload
```

The archive is extracted into isolated project storage. Python files are
discovered recursively, including files under a `backend/` directory. The
scanner does not execute uploaded code.

Ignored directories include:

```text
.git
__pycache__
venv
.venv
node_modules
dist
build
```

After upload, start the full background scan from the project page or:

```text
POST /api/projects/{project_id}/scan
```

### GitHub repository

Import a repository with:

```text
POST /api/projects/github
```

The request accepts a GitHub HTTPS repository URL and branch/ref. The
repository is downloaded into isolated storage and queued through the same
scan pipeline.

### GitHub pull requests

Configure:

```env
GITHUB_TOKEN=...
GITHUB_WEBHOOK_SECRET=...
```

Set the GitHub webhook URL to:

```text
POST /api/webhooks/github
```

Enable JSON `pull_request` events. Supported actions are `opened`, `reopened`,
and `synchronize`.

The worker:

1. Validates the signed webhook.
2. Reads the changed-file list.
3. Skips PRs without Python backend changes.
4. Downloads the PR head snapshot.
5. Reuses stored hashes and indexes to analyze affected files and dependencies.
6. Posts a concise security comment to the pull request.

## API overview

| Area | Endpoint |
| --- | --- |
| Health | `GET /health` |
| Projects | `GET /api/projects` |
| Project details | `GET /api/projects/{id}` |
| ZIP upload | `POST /api/projects/upload` |
| GitHub import | `POST /api/projects/github` |
| Start scan | `POST /api/projects/{id}/scan` |
| Scan status | `GET /api/scans/{id}` |
| Scan history | `GET /api/projects/{id}/scans` |
| Project findings | `GET /api/projects/{id}/findings` |
| All findings | `GET /api/findings` |
| Finding details | `GET /api/findings/{id}` |
| GitHub webhook | `POST /api/webhooks/github` |

Finding list endpoints support `severity`, `endpoint`, `rule`, `offset`, and
`limit`. The maximum page size is 100.

## Production configuration

Set:

```env
ENVIRONMENT=production
API_AUTH_ENABLED=true
API_KEYS=replace_with_a_long_random_key
RATE_LIMIT_ENABLED=true
```

Clients must send:

```text
X-API-Key: replace_with_a_long_random_key
```

Use strong, unique secrets for:

- `API_KEYS`
- `GITHUB_TOKEN`
- `GITHUB_WEBHOOK_SECRET`
- `GROQ_API_KEY`
- PostgreSQL credentials

Never commit `.env`, `.env.local`, API keys, tokens, or provider credentials.
ZIP uploads have compressed-size, decompressed-size, file-count, and
per-member limits. Redis-backed rate limiting protects expensive API paths.

## Database migrations

From `backend`:

```powershell
alembic upgrade head
```

Create a migration:

```powershell
alembic revision --autogenerate -m "describe change"
```

## Testing

From `backend`:

```powershell
.\.venv\Scripts\Activate.ps1
pytest
```

Tests are restricted to `backend/tests`; uploaded files in
`backend/storage` are not collected.

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Repository structure

```text
backend/
  app/
    api/          FastAPI routes
    core/         configuration, auth, logging, rate limiting
    db/           database session and base
    models/       SQLAlchemy models
    schemas/      Pydantic API schemas
    services/     scanning, AI, GitHub, indexing, graph, and rules
  migrations/    Alembic migrations
  tests/         backend tests
frontend/
  app/            Next.js App Router pages
  components/     reusable UI components
  lib/            frontend API client
docker-compose.yml
```

## Security boundaries

SecGraph analyzes uploaded source as data. It does not run project commands,
install project dependencies, or execute uploaded Python code. AI providers
receive compact finding context rather than the complete repository.

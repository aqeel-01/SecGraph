# SecGraph Backend

Backend foundation for the SecGraph API Security Reviewer.

## Requirements

- Python 3.11+
- PostgreSQL

## Setup

From the `backend` directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `DATABASE_URL` in `.env` for the local PostgreSQL instance.
Set `STORAGE_DIR` to change where uploaded projects are extracted. Uploads are
limited by `MAX_UPLOAD_SIZE_BYTES` (50 MiB by default).

## Run

```powershell
uvicorn app.main:app --reload
```

Run a Celery worker in a second terminal:

```powershell
celery -A app.services.scan_tasks.celery_app worker --loglevel=INFO
```

The health check is available at `GET http://127.0.0.1:8000/health`.
Project ZIPs can be uploaded at `POST /api/projects/upload` using the `file`
multipart field.
Scans are queued with `POST /api/projects/{project_id}/scan` and queried with
`GET /api/scans/{scan_id}`.
Uploads are preprocessed for Python source files, SHA-256 metadata, declared
Python versions, FastAPI usage, and API routes. Files in common generated or
dependency directories are excluded.

The preprocessing pipeline currently:

- Records Python file paths, sizes, languages, and SHA-256 hashes.
- Detects declared Python versions and FastAPI usage.
- Indexes imports, classes, functions, parameters, decorators, calls, and
  assignments using Python's built-in `ast` module.
- Detects FastAPI app and router routes, including methods, paths, and
  dependencies.
- Builds a relational code graph with file, module, function, route, and
  database/authentication call nodes.
- Stores `CALLS`, `IMPORTS`, and `ROUTES_TO` relationships in PostgreSQL.
- Stores syntax errors separately without stopping other files from indexing.
- Runs deterministic static checks for missing authentication, possible IDOR,
  SQL injection patterns, hardcoded secrets, sensitive data exposure, and
  missing rate limiting.
- Persists each finding with a compact JSON context package containing only the
  affected endpoint, function, relevant source, dependencies, operations, and
  graph relationships.
- Executes the complete scan pipeline as a Celery background task backed by
  Redis.
- Uses stored SHA-256 hashes for incremental scans, reindexing only added or
  modified files plus files that depend on them.

## Test

```powershell
pytest
```

## Database migrations

Alembic is configured in `alembic.ini` and `migrations/`. Create and apply
migrations with:

```powershell
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The current migration chain includes project/scan storage, preprocessing
metadata, the Python AST index, detected API routes, the relational code graph,
static findings, compact finding context, AI routing records, and validated
explanations. Static findings are stored in `security_findings`.
Finding context is stored in the `context_package` JSON column and is designed
for future AI analysis without sending the entire repository.

## AI providers

The provider abstraction is available through `AIProvider.analyze(context)`.
It currently includes:

- Ollama using `OLLAMA_BASE_URL` and `OLLAMA_MODEL`
- Groq using `GROQ_API_KEY` and `GROQ_MODEL`

The default models are `deepseek-r1:1.5b` for Ollama and `deepseek-r1:7b`
for Groq. Provider calls use `AI_TIMEOUT_SECONDS` and return structured
success or error responses.

The configurable routing layer skips AI for high-confidence deterministic
findings, uses Ollama for simple findings, and prefers Groq for complex
findings when configured. Groq failures fall back to Ollama. Routing decisions,
provider attempts, selected model, and optional AI confidence are stored in
`ai_analyses`.

AI responses must contain validated JSON with severity, confidence,
explanation, potential attack, impact, and suggested fix fields. Malformed
responses are recorded safely and are never treated as validated analysis.

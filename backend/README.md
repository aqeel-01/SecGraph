# SecGraph Backend

Initial backend foundation for the SecGraph API Security Reviewer.

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

The health check is available at `GET http://127.0.0.1:8000/health`.
Project ZIPs can be uploaded at `POST /api/projects/upload` using the `file`
multipart field.

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

No domain models or migrations are included in this initial foundation.

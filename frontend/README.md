# SecGraph Frontend

Next.js and TypeScript dashboard for the SecGraph API Security Reviewer.

## Run

```powershell
npm install
Copy-Item .env.example .env.local
npm run dev
```

The frontend expects the FastAPI API at
`NEXT_PUBLIC_API_BASE_URL` and is available at `http://localhost:3000`.

Pages include the dashboard, project list/upload/detail views, scan progress,
security findings, and finding details.

The upload page also supports selecting a GitHub HTTPS repository and branch;
the backend downloads it into isolated storage and queues the existing scan
pipeline.

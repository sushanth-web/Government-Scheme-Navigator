# SchemeSage

The application is split into two deployable projects:

- `frontend/` — React + TypeScript + Vite user interface.
- `backend/` — FastAPI API, Python agents, scheme documents, and backend data.

## Deploy the frontend to Vercel

Import the repository into Vercel and set **Root Directory** to `frontend`.
Vercel uses the included `vercel.json` to build the Vite app and serve
client-side routes. Set `VITE_API_BASE_URL` in the Vercel project's
environment variables to the public HTTPS URL of the deployed backend API
(without a trailing slash). This value is public; do not put provider or
database secrets in frontend environment variables.

The backend is a separate FastAPI service. Deploy it to a host that supports
the backend's Python dependencies, persistent Postgres connections, and
scheme-document/index assets. Set its production secrets and set
`FRONTEND_ORIGINS` to the exact HTTPS Vercel site origin.

## Run locally

Set up the backend from PowerShell:

```powershell
if (-not (Test-Path backend\.env)) {
  Copy-Item backend\.env.example backend\.env
}
Set-Location backend
python -m pip install -r requirements.txt
uvicorn api:app --reload
```

Add provider/database credentials to `backend\.env`. If a local `backend\.env`
already exists, edit it instead of overwriting it.

In another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Vite proxies `/api` to the local backend at `http://127.0.0.1:8000`.

# SchemeSage

SchemeSage is a conversational guide for exploring government schemes. People
can share information by text or voice, review possible scheme matches, and get
practical next steps and a document checklist. The interface supports ten
languages. SchemeSage is an independent guide and is not an official
government website; users should confirm current eligibility and application
details with the relevant department.

## Contents

- [Features](#features)
- [Architecture and technologies](#architecture-and-technologies)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Local setup](#local-setup)
- [Environment variables](#environment-variables)
- [Run the application](#run-the-application)
- [Tests and maintenance](#tests-and-maintenance)
- [API overview](#api-overview)
- [Deployment to Vercel](#deployment-to-vercel)
- [Troubleshooting](#troubleshooting)
- [Security and privacy](#security-and-privacy)

## Features

- Conversational scheme discovery based on information a user chooses to share.
- Text and audio input, with streamed conversation responses.
- Scheme retrieval from the included documents and a prebuilt Chroma index.
- Scheme selection and personalized document checklists.
- Ten interface languages: Bengali, English, Gujarati, Hindi, Kannada,
  Malayalam, Marathi, Punjabi, Tamil, and Telugu.
- Optional PostgreSQL-backed conversation persistence with an expiry period.
- Responsive React interface and Vercel Web Analytics integration.

## Architecture and technologies

The application is split into two deployable parts:

- **Frontend:** React 18, TypeScript, Vite, React Router, and Lucide icons.
  Vercel Analytics is integrated through `@vercel/analytics`.
- **Backend:** Python 3.12+, FastAPI, and Uvicorn. LangChain and LangGraph
  coordinate the conversational agents; NVIDIA provides the configured chat
  and embedding models.
- **Retrieval:** ChromaDB stores the vector index. Scheme PDFs and the
  prebuilt index are kept under `backend/data/`.
- **Persistence:** PostgreSQL through Psycopg; Neon is supported. If no
  database URL is configured during local development, sessions use temporary
  in-memory storage instead.
- **External services:** NVIDIA, Gnani speech services, and Tavily are
  configured through backend environment variables.
- **Deployment:** Vercel can host the frontend and backend as separate
  projects, or route them together as Vercel Services.

## Repository layout

```text
.
├── backend/
│   ├── agents/             # Conversation, retrieval, and audio agents
│   ├── data/
│   │   ├── cache/          # Prebuilt Chroma index and manifest
│   │   └── schemes/        # Scheme source PDFs
│   ├── tests/              # Backend tests
│   ├── api.py              # FastAPI application and API routes
│   ├── session_store.py    # In-memory/PostgreSQL session storage
│   ├── requirements.txt    # Local development dependencies
│   └── pyproject.toml      # Vercel backend entrypoint/dependencies
├── frontend/
│   ├── public/             # Static assets, including the SchemeSage logo
│   ├── src/                # React app, screens, styles, and language copy
│   ├── package.json
│   └── vercel.json
├── pyproject.toml          # Root Vercel FastAPI entrypoint
└── vercel.json             # Combined Vercel Services and routing config
```

## Requirements

- Python 3.12 or later.
- Node.js LTS and npm.
- Git (to clone the repository).
- API credentials for the providers you want to use. The backend uses
  `NVIDIA_API_KEY` for model access, `GNANI_API_KEY` for speech services, and
  `TAVILY_API_KEY` for official-source search.
- A PostgreSQL database is optional for local use and required for persistent
  sessions in production.

## Local setup

Clone the repository and open a terminal at its root directory.

### 1. Create and activate a Python environment

PowerShell:

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks environment activation, either allow scripts for the
current terminal according to your organization’s policy or call the
environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

macOS/Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 2. Configure the backend

Copy the example file and edit it:

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Set the required provider credentials in `backend/.env`; see
[Environment variables](#environment-variables). If you do not have a
PostgreSQL database for local development, remove or comment out the example
`DATABASE_URL` line. Leaving the sample placeholder in place will make the
backend try to connect to it.

### 3. Install frontend dependencies

Open a second terminal at the repository root:

```powershell
cd frontend
npm install
```

For macOS/Linux, use the same commands in a shell. The committed
`frontend/package-lock.json` keeps npm dependency versions reproducible.

## Environment variables

Backend variables belong in `backend/.env` locally and in the backend
deployment's environment-variable settings in production. Do not put provider
keys or database credentials in frontend variables.

| Variable | Required | Purpose |
| --- | --- | --- |
| `NVIDIA_API_KEY` | Yes for model-powered conversations | Authenticates NVIDIA chat and embedding requests. |
| `GNANI_API_KEY` | Yes for speech input | Authenticates speech transcription requests. |
| `TAVILY_API_KEY` | Yes for external scheme-source search | Authenticates Tavily search requests. |
| `DATABASE_URL` | Optional locally; required in production | PostgreSQL connection string. Use a provider-issued SSL connection URL. |
| `APP_ENV` | No; defaults to development | Set to `production` for production-specific validation and behavior. |
| `FRONTEND_ORIGINS` | Required when `APP_ENV=production` | Comma-separated exact HTTPS origins allowed by backend CORS. Use origins only, with no path or trailing slash. |
| `SESSION_TTL_HOURS` | No; defaults to `24` | Session inactivity expiry period in hours. |
| `DATABASE_POOL_SIZE` | No; defaults to `3` | Maximum PostgreSQL session-store connection pool size. |
| `CHECKPOINT_POOL_SIZE` | No; defaults to `3` | Maximum PostgreSQL checkpoint connection pool size. |
| `MAX_CONCURRENT_REQUESTS` | No; defaults to `8` | Backend request concurrency limit. |

`frontend/.env.example` documents `VITE_API_BASE_URL`. For a separate frontend
deployment, set this to the backend's public HTTPS origin, without a trailing
slash. For the combined same-domain Services deployment, leave it empty so the
frontend calls the same-origin `/api` routes.

Vite variables prefixed with `VITE_` are embedded in the public frontend build.
Only put public configuration there; never put API keys or database URLs in
frontend environment variables.

## Run the application

Start the backend from the `backend/` directory with its virtual environment
active:

```powershell
uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Open the local URL printed by Vite (normally `http://localhost:5173`). During
development, Vite proxies requests under `/api` to `http://127.0.0.1:8000`.
The backend health endpoint is available at
`http://127.0.0.1:8000/api/health`.

To create a production frontend build locally:

```powershell
cd frontend
npm run build
```

The build output is written to `frontend/dist/`.

## Tests and maintenance

Run the backend tests from `backend/` with the virtual environment active:

```powershell
python -m unittest discover -s tests -v
```

The checked-in Chroma index is used by the application. If you intentionally
change the scheme PDFs and need to rebuild the index, install the local
dependencies from `backend/requirements.txt`, configure the required NVIDIA
embedding credentials, and run:

```powershell
cd backend
python -m agents.build_index
```

Index generation calls the embedding provider and updates files under
`backend/data/cache/`; do not run it just to start the application.

## API overview

All API paths are under `/api`. The frontend creates a session only after the
user accepts the privacy notice.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Check API and session-store health. |
| `POST` | `/api/sessions` | Create a session after consent. |
| `PUT` | `/api/sessions/{session_id}/language` | Set the session language and start the conversation. |
| `POST` | `/api/sessions/{session_id}/messages` | Send a text message. |
| `POST` | `/api/sessions/{session_id}/audio` | Submit audio for transcription and conversation. |
| `DELETE` | `/api/sessions/{session_id}` | End and delete a conversation. |

Conversation responses are streamed using Server-Sent Events. Opening
`/api/sessions` in a browser sends a `GET`; this endpoint only accepts `POST`,
so a `405 Method Not Allowed` response to that browser navigation is expected.

## Deployment to Vercel

### Combined frontend and backend in one project

The root `vercel.json` defines a frontend and a FastAPI backend as Vercel
Services. Configure the Vercel project as follows:

1. Import the repository and set **Root Directory** to `./`.
2. Select the **Services** framework preset so Vercel uses the root Services
   configuration.
3. Configure the backend secrets and `DATABASE_URL` as Vercel environment
   variables. Set `APP_ENV=production` and set `FRONTEND_ORIGINS` to the exact
   production frontend origin, such as `https://your-project.vercel.app`.
4. Deploy. The root routing sends `/api/*` to FastAPI and every other path to
   the frontend.
5. Enable Web Analytics in the Vercel project settings if you want to view the
   analytics collected by the frontend integration.

The frontend uses relative `/api` URLs in this setup, so
`VITE_API_BASE_URL` is not needed. The Python runtime copies the prebuilt
Chroma index to writable temporary storage on Vercel; the bundled function
filesystem itself is read-only.

### Deploy frontend and backend as separate Vercel projects

Create two Vercel projects from the same repository:

- **Frontend:** set **Root Directory** to `frontend`. Set
  `VITE_API_BASE_URL` to the backend's public HTTPS origin, without a trailing
  slash. Configure the `frontend/` Vercel project to build the Vite app.
- **Backend:** set **Root Directory** to `backend`. The backend
  `pyproject.toml` specifies the `api:app` FastAPI entrypoint. Configure
  backend secrets, `APP_ENV=production`, and `FRONTEND_ORIGINS` with the exact
  HTTPS origin of the frontend project.

Do not configure the backend project to run `npm run build`; the frontend and
backend are separate builds in this deployment model.

## Troubleshooting

- **Frontend cannot reach the API:** verify the backend is running and healthy.
  With separate Vercel projects, check that `VITE_API_BASE_URL` is set to the
  backend origin and that the backend allows the frontend in
  `FRONTEND_ORIGINS`. Rebuild/redeploy the frontend after changing a `VITE_`
  variable.
- **`405 Method Not Allowed` at `/api/sessions`:** the route is a `POST`
  endpoint. Test `/api/health` with `GET` or create a session from the app.
- **`/` returns `{"detail":"Not Found"}` instead of the UI:** the root URL is
  reaching FastAPI. For a combined deployment, verify the Vercel project uses
  the **Services** preset and the root `vercel.json` configuration.
- **Database startup or health failure:** check that `DATABASE_URL` is a valid
  PostgreSQL SSL connection string and that the database accepts connections
  from the deployment.
- **Provider errors during conversation:** check that the required backend
  API keys are present in the correct environment and that the provider account
  has access to the configured models/services.
- **Python dependency or entrypoint errors:** check the Vercel project's root
  directory. A backend-only project should use `backend`; a combined Services
  project should use the repository root and the **Services** preset.

## Security and privacy

- Never commit `.env` files, API keys, database URLs, or other credentials.
- If a credential is accidentally exposed, revoke or rotate it with its
  provider and update the deployment environment variables.
- Keep secrets in backend environment variables only. `VITE_` variables are
  public to every visitor of the frontend.
- Conversation details are stored in the configured session store and expire
  after the configured inactivity period. Users can end a conversation from
  the app.
- Voice recordings are sent to the configured speech transcription provider.
  Review provider terms and the in-app privacy notice before deploying for
  real users.
- Scheme information can change. Confirm official eligibility rules and
  application instructions with the relevant government department.

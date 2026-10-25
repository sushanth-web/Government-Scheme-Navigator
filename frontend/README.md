# SchemeSage frontend

Responsive React + TypeScript application for the SchemeSage landing page,
language selection, and conversational demo.

## Run locally

From this folder:

```powershell
npm install
npm run dev
```

Open the local URL printed by Vite. To create and preview a production build:

```powershell
npm run build
npm run preview
```

## User flow

- `/` — Landing page with “Try now” and no account or login flow.
- `/language` — Choose Hindi, Bengali, Gujarati, English, Telugu, Marathi,
  Tamil, Kannada, Malayalam, or Punjabi.
- `/conversation` — Interactive demo chat with step-by-step profile questions,
  optional scheme-relevant profile details that can be skipped, selectable
  schemes, and a sample document checklist.

The language choice is saved in local storage. Before starting, the app shows a
privacy notice and asks for affirmative consent. Chat and profile details are
stored by the API and deleted when the user ends the session or the inactivity
expiry is reached.

## Backend connection status

The conversation UI uses the FastAPI backend and Python LangGraph agents.

1. If `backend/.env` does not exist, copy `backend/.env.example` to
   `backend/.env`; otherwise edit the existing file without overwriting it.
2. Set `DATABASE_URL` to the Neon **direct** connection string (include
   `sslmode=require`), and set `NVIDIA_API_KEY`, `GNANI_API_KEY`, and
   `TAVILY_API_KEY` in that local `.env` file. Do not put server keys in
   frontend variables or paste them into chat.
3. Install the Python packages from `backend/`. Audio conversion
   uses a system FFmpeg when available and the `imageio-ffmpeg` package
   otherwise; the container image installs FFmpeg.
4. Start the backend from `backend/`:

```powershell
python -m pip install -r requirements.txt
uvicorn api:app --reload
```

5. From `frontend/`, run `npm install` once and `npm run dev`. Vite proxies
   `/api` to `http://127.0.0.1:8000`.

The API provides `POST /api/sessions`, `PUT /api/sessions/{id}/language`,
`POST /api/sessions/{id}/messages`, `POST /api/sessions/{id}/audio`,
`DELETE /api/sessions/{id}`, and `GET /api/health`. Browser recording uses
`MediaRecorder`; uploaded WebM/MP4 audio is converted to WAV with FFmpeg before
transcription. Responses use server-sent events parsed from `fetch()` streams
(native `EventSource` only supports GET). The reply event includes readable
text and optional WAV audio as base64. When **Spoken replies** is enabled, new
replies are spoken automatically; the app falls back to browser speech when
provider audio is unavailable or autoplay is blocked. Browser playback policies
vary, so the text always remains available and the interface reports when
automatic speech cannot start.

Session data is stored in Neon Postgres, LangGraph checkpoints use the same
Postgres database, and inactivity refreshes the expiry (24 hours by default;
set `SESSION_TTL_HOURS` to change it). Expired rows and checkpoints are
purged automatically. Without `DATABASE_URL`, development deliberately falls
back to temporary in-memory sessions; production mode refuses to start without
Postgres. Scheme results are not an official eligibility determination.

### Updating scheme PDFs

The backend does not rebuild Chroma automatically when it starts. After adding,
replacing, or deleting PDFs in `backend/data/schemes`, run this from `backend/`
before restarting the API:

```powershell
python -m agents.build_index
```

This rebuilds the local index from the current PDF set and removes vectors from
the previous index. The API checks a content-hash manifest and refuses to serve
stale results if the PDFs change without an index rebuild. For Docker
deployments, rebuild the image after changing scheme PDFs; its index is baked
into the image and read-only at runtime.

The user can also select **End and delete** at any time. NVIDIA and Gnani
receive conversation content for inference/transcription. Tavily searches
scheme names only, never profile details, and the search is restricted to
government domains. When scheme PDFs do not provide a usable application
checklist (or dates are missing), the checklist agent searches those official
domains with Tavily and uses only scheme-relevant results. Official result
links are shown with the generated checklist; if Tavily is unavailable or
returns no usable information, the checklist marks the missing details rather
than inventing requirements. Confirm each provider's data-processing and
retention terms before collecting real personal data.

The Docker image installs FFmpeg and builds the Chroma index from
`data/schemes` during image construction. Run the Docker commands below from
the `backend/` directory. The indexed directory is shipped without write
permissions and runtime code only searches it. Build with
Docker BuildKit and provide `NVIDIA_API_KEY` as a build secret (never a build
argument); from PowerShell, load the key into the current process environment
from your local `.env`, then run:

```powershell
$entry = Get-Content .env | Where-Object { $_ -match '^\s*NVIDIA_API_KEY=' } | Select-Object -First 1
$env:NVIDIA_API_KEY = ($entry -split '=', 2)[1].Trim().Trim('"').Trim("'")
docker build --secret id=nvidia_api_key,env=NVIDIA_API_KEY -t schemesage-api .
Remove-Item Env:NVIDIA_API_KEY
docker run --env-file .env -e APP_ENV=production -p 8000:8000 schemesage-api
```

Pass the runtime `.env` to the container for Neon, NVIDIA, and Gnani settings.
Do not mount a writable volume over `/app/data/cache`.

For a Neon cold-start check before a demo, call `GET /api/health` after the
database has been idle and note the response time, then create a session and
send a message. The conversation page shows a loading state throughout
connection, model, transcription, and voice-generation delays. The health
endpoint reports `storage: "postgres"` when Neon is active.

## Production safeguards

- Set `APP_ENV=production` and `FRONTEND_ORIGINS` to the exact HTTPS origin(s)
  serving the frontend, such as `https://schemes.example.in`. Production
  startup rejects missing, wildcard, or non-HTTPS origins. HTTP is redirected
  to HTTPS; terminate TLS at a trusted ingress/load balancer and forward the
  original HTTPS scheme.
- The API caps concurrent requests at eight per process by default
  (`MAX_CONCURRENT_REQUESTS`) and applies per-IP rate limits. These are
  process-local demo safeguards, not a distributed limiter. Use a shared
  gateway/limiter before adding workers or replicas.
- The expiry sweeper runs for the lifetime of the API process. Configure your
  host for at least one minimum replica where possible; free hosting may still
  suspend idle apps and cause cold starts.
- From `backend/`, load-test health and session storage with Locust (this avoids
  paid inference):

```powershell
python -m pip install -r requirements-load.txt
locust -f locustfile.py --host http://127.0.0.1:8000
```

Start with a small test, for example 8 users at 2 users/second. `429` and
`503` responses are expected if configured rate or concurrency limits are
exceeded. Do not run provider-backed load tests against production without an
approved budget and isolated test data.

### India privacy note

The DPDP Act, 2023 does not create a separate statutory “sensitive personal
data” category for caste or income, but SchemeSage treats them as high-risk
personal information and minimizes collection. The prototype now requires an
affirmative notice acceptance, stores consent time/version, supports early
deletion, and purges sessions/checkpoints after expiry. This alone does not
establish legal compliance. Before public launch, obtain India-specific legal
review and implement/verify the applicable notice details, withdrawal and
grievance process, processor contracts, reasonable safeguards, breach
response/notifications, and any child-user restrictions. Check the current Act
and Rules on the [MeitY data protection framework](https://www.meity.gov.in/data-protection-framework)
and the [eGazette of India](https://egazette.gov.in/).

## Design references and Draftly prompts

See [DRAFTLY_PROMPTS.md](./DRAFTLY_PROMPTS.md) for the product brief, navigation
map, image/motion/video prompts, and reference-asset index. The reference SVGs
are under `public/references/`; `schemesage-intro-clip.svg` is an animated
vector intro, not an MP4 export.

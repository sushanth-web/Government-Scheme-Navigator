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
  selectable example schemes, and a sample document checklist.

The language choice is saved in local storage. Chat and profile details are not
persisted. When available in the browser, speech synthesis reads assistant
messages and the Web Speech API can transcribe microphone input.

## Backend connection status

The chat and scheme results are illustrative frontend behavior, not connected
to the Python LangGraph agents or live government scheme data. Browser speech
support and language voices vary by browser and installed operating-system
voices. A production deployment needs an authenticated backend/API for agent
responses, official source citations, speech services, secure profile storage,
and explicit privacy/retention controls. Do not put provider API keys in this
frontend.

## Design references and Draftly prompts

See [DRAFTLY_PROMPTS.md](./DRAFTLY_PROMPTS.md) for the product brief, navigation
map, image/motion/video prompts, and reference-asset index. The reference SVGs
are under `public/references/`; `schemesage-intro-clip.svg` is an animated
vector intro, not an MP4 export.

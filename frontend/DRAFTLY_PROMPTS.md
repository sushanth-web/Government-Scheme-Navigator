# SchemeSage — Draftly AI creative brief and prompts

## Website brief

Create a responsive, accessible public-benefits discovery website called
**SchemeSage**. The product helps people explore government-scheme information
through a supportive voice-and-text conversation. It is an independent
information assistant, not a government website and not an eligibility
authority.

### Audience and tone

- People who may be unfamiliar with government websites, digital forms, or
  scheme terminology.
- Warm, respectful, reassuring, plain-language, and never bureaucratic.
- Do not imply that a person is guaranteed to qualify or receive benefits.
- Give users control: they can type, speak, change language, and skip
  non-essential answers.

### Brand and visual direction

- Brand: SchemeSage.
- Use a warm paper/cream background, deep evergreen text, natural sage accents,
  and a restrained amber highlight.
- Avoid the previous dark teal-and-neon appearance. Keep the interface light,
  calm, editorial, tactile, and optimistic.
- Use soft paper-like cards, quiet thin borders, rounded corners, generous
  whitespace, fine grain only if subtle, and accessible color contrast.
- Use dimensional but restrained 3D illustration: a friendly glowing voice
  orb, gentle orbit lines, floating scheme cards, small botanical or civic
  motifs. Keep text legible and interactions clear.
- Do not use government seals, official emblems, or imagery that implies
  government endorsement.
- Respect `prefers-reduced-motion`; motion should be ambient and never obstruct
  reading or controls.

### Required navigation and product flow

1. **Landing page `/`**
   - Header: SchemeSage mark, “How it works”, “Languages”, “Your privacy”, and
     “Try now”.
   - Hero: “Find schemes that fit. Just by talking.” Explain the service in
     plain English. Primary CTA is “Try now”; no sign-up or login.
   - Show the three-step process: share relevant details, explore possible
     scheme matches, get a document checklist.
   - Include supported-language preview, privacy reassurance, an independent
     information disclaimer, and another “Try now” CTA.
2. **Language page `/language`**
   - Ask which language the user wants to speak before conversation begins.
   - Offer Hindi, Bengali, Gujarati, English, Telugu, Marathi, Tamil, Kannada,
     Malayalam, and Punjabi. Show each name in native script and English.
   - Clearly show the selected language and offer a “Start conversation” action.
3. **Conversation page `/conversation`**
   - A calm chat layout with assistant status, progress, and a compact profile
     summary.
   - Ask one short question at a time, in the selected language. Show assistant
     replies as text and provide audio playback. Let the user type or use voice
     input where supported.
   - Provide a visible “thinking”/loading state and recording/speaking states.
   - After intake, show possible scheme matches with an explicit “example /
     check official criteria” caveat. Let the user select schemes and receive a
     document checklist.
   - Do not ask for Aadhaar number, phone number, bank-account details,
     passwords, or OTPs.
   - On mobile, make the conversation the focus and keep voice/text controls
     reachable with one hand.
4. Provide a clear way to return home or change language. Never introduce
   login/sign-up screens.

### Copy and trust

- Say “possible match” or “may be relevant,” never “you qualify” unless an
  authoritative backend has checked criteria and sources.
- Show source/date and explain that details can change.
- Clearly distinguish the demo from live eligibility results.
- Describe what data is collected, why, where it is stored, and how to delete
  it before production deployment.

## Prompt: generate landing-page hero image

> Create a premium, warm editorial 3D illustration for “SchemeSage”, a
> multilingual public-benefits discovery assistant. Main subject: a gentle,
> amber-gold voice orb floating over a warm cream paper background, surrounded
> by very fine sage-green orbit lines. Add three small, tilted, tactile paper
> cards suggesting farming support, student assistance, and a useful document
> checklist; use abstract line icons and tiny placeholder marks only, no
> readable generated text. Include a few subtle botanical/civic geometry details.
> Palette: evergreen #173D35, sage #477861, cream #F7F6F1, muted amber #EDAA4B,
> soft peach #F8E4CF. Soft studio lighting, gentle contact shadows, friendly,
> calm, trustworthy, accessible, generous negative space. Wide landscape 3:2
> composition. Keep the left third mostly clear for website headline overlay.
> No people, no flags, no government seals, no logos, no watermarks, no claims
> of eligibility, no dark teal background, no neon.

## Prompt: three interface reference images

> Produce a consistent set of three high-fidelity UI reference images for one
> product called SchemeSage, all with a light warm-cream canvas, evergreen
> typography, sage-green accents, and a restrained amber action color. Image 1:
> desktop landing page with simple header, hero headline “Find schemes that fit.
> Just by talking.”, clear “Try now” button, friendly orb illustration and
> three-step explainer. Image 2: language selection screen with ten native-script
> language tiles and a clear selected state. Image 3: accessible desktop chat
> interface with one assistant question, user reply, optional “Speaking”
> status, visible audio and text controls, a loading state, and compact profile
> sidebar. Use the supplied SchemeSage SVG reference images as layout/color
> references. Keep typography crisp and secondary UI labels short. No login,
> sign-up, government logos, or guaranteed-eligibility language.

## Prompt: motion system / image motion

> Animate the SchemeSage hero illustration as a subtle 6–8 second seamless
> loop. The central amber voice orb floats vertically by only 5–8 px and softly
> pulses in brightness; thin orbit rings draw on gently; paper scheme cards
> drift independently by 3–5 px with a slight slow parallax tilt; one tiny
> sparkle glints once, then rests. Keep cards and text readable and stable.
> Easing is slow and organic, with no camera shake, fast zoom, flashing,
> particle storm, or looping layout jump. Preserve the cream / evergreen / sage
> / amber palette. Provide a reduced-motion version with a static image.

## Prompt: video clip

> Create a polished 12-second 16:9 product introduction for SchemeSage at
> 1920×1080, 24 fps. Shot 1 (0–2 s): warm cream paper background; the outlined
> SchemeSage shield-check draws on. Shot 2 (2–5 s): soft amber voice orb blooms
> into view; very fine sage orbit lines trace around it; abstract scheme cards
> float in from the edges. Shot 3 (5–8 s): transition to a clean conversation
> UI; an assistant asks one short question, a user replies by voice, then a
> compact “thinking” indicator appears. Do not use real personal data. Shot 4
> (8–10 s): show a few example scheme cards and a clear document checklist with
> a visible “confirm official details” caveat. Shot 5 (10–12 s): end card with
> SchemeSage wordmark and “A clearer path to public benefits”, plus a “Try now”
> label. Use restrained motion, natural shadows, large legible type, and
> accessible contrast. Sound: gentle two-note marimba/piano motif, a soft voice
> chime, no narration required. No official seals, no fake endorsements, no
> claims that a user is eligible. Deliver a 16:9 MP4 plus a silent version.

### Included motion reference clip

`public/references/schemesage-intro-clip.svg` is a six-second looping animated
SVG brand-intro reference that can be opened in a browser or imported into
motion software. This environment did not have a video encoder available, so
an MP4 has not been generated.

## Prompt: navigation and interaction

> Implement the exact SchemeSage flow: `/` landing → “Try now” → `/language`
> language selection → “Start conversation” → `/conversation` chat. Keep a
> visible home/back action and a “Change language” control in the conversation.
> No login or account creation anywhere. The language choice persists on this
> device and sets the conversation locale. Add keyboard focus states, semantic
> buttons, screen-reader labels, Escape/back behavior where appropriate, and
> responsive navigation. A loading state should announce itself accessibly.
> Mark any simulated scheme results as demo content and never represent browser
> speech recognition as a production service connection.

## Prompt: website implementation

> Build a responsive React + TypeScript website called SchemeSage using the
> provided references and brief. Use reusable typed components, real client-side
> navigation, accessible semantic HTML, responsive CSS, and reduced-motion
> support. Add ten languages with native-script names. The chat demo should ask
> one profile question at a time, show a visible loading state, support typed
> responses and browser speech APIs where available, offer speech playback for
> assistant messages, display selectable example scheme cards, then show a
> sample document checklist. Persist only the selected language locally; do not
> store chat/profile data in browser storage. Clearly mark the chat and results
> as illustrative until an authenticated backend is connected. Do not create
> login/sign-up pages or hard-code API keys.

## Navigation map

```text
Landing /
  ├── How it works → section
  ├── Languages → section
  ├── Your privacy → section
  └── Try now → Language selection /language
        └── Select language → Start conversation
              └── Conversation /conversation
                    ├── Change language → /language
                    ├── Answer by text or voice
                    ├── Choose example schemes
                    └── Build sample checklist → Finish / landing
```

## Reference assets

- `public/references/01-landing-page.svg` — desktop landing-page composition.
- `public/references/02-language-selection.svg` — all ten language choices.
- `public/references/03-conversation-screen.svg` — desktop conversational UI.
- `public/references/04-mobile-conversation.svg` — mobile conversational UI.
- `public/references/schemesage-intro-clip.svg` — animated SVG identity clip.

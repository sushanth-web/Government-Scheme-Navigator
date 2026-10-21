import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  AudioLines,
  Check,
  CheckCircle2,
  CircleHelp,
  FileCheck2,
  Globe2,
  Leaf,
  LoaderCircle,
  LockKeyhole,
  Menu,
  Mic,
  MicOff,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  Volume2,
  X,
} from "lucide-react";
import {
  Link,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { getConversationCopy } from "./data/conversation";
import { languages } from "./data/languages";
import type {
  AppLanguage,
  ChatMessage,
  ProfileField,
  TurnResponse,
} from "./types";

const LANGUAGE_STORAGE_KEY = "schemesage-language";
const PRIVACY_NOTICE_VERSION = "2026-10-21";

function getRequestError(error: unknown): string {
  if (error instanceof TypeError) {
    return "Could not reach SchemeSage. Check your internet connection and try again.";
  }
  return error instanceof Error ? error.message : "Unable to reach the assistant.";
}

function readSavedLanguage(): AppLanguage | null {
  try {
    const saved = window.localStorage.getItem(LANGUAGE_STORAGE_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as { locale?: string };
    return languages.find((language) => language.locale === parsed.locale) ?? null;
  } catch {
    return null;
  }
}

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link className={`brand ${compact ? "brand-compact" : ""}`} to="/" aria-label="SchemeSage home">
      <span className="brand-emblem" aria-hidden="true">
        <ShieldCheck size={21} strokeWidth={1.9} />
      </span>
      <span>Scheme<span className="brand-sage">Sage</span></span>
    </Link>
  );
}

function SiteHeader() {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="site-header">
      <Brand />
      <nav className={menuOpen ? "main-nav main-nav-open" : "main-nav"} aria-label="Main navigation">
        <a href="/#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
        <a href="/#languages" onClick={() => setMenuOpen(false)}>Languages</a>
        <a href="/#privacy" onClick={() => setMenuOpen(false)}>Your privacy</a>
      </nav>
      <Link className="button button-dark header-cta" to="/language">
        Try now <ArrowRight size={15} />
      </Link>
      <button className="menu-toggle" type="button" aria-label={menuOpen ? "Close navigation" : "Open navigation"} onClick={() => setMenuOpen((open) => !open)}>
        {menuOpen ? <X size={21} /> : <Menu size={21} />}
      </button>
    </header>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <Brand compact />
      <p>SchemeSage is an independent guide, not an official government website. Please confirm scheme details with the relevant department.</p>
      <a href="#top">Back to top <ArrowRight size={13} /></a>
    </footer>
  );
}

function LandingPage() {
  const navigate = useNavigate();

  return (
    <>
      <SiteHeader />
      <main id="top">
        <section className="hero page-shell">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-spark"><Sparkles size={13} /></span> A friendlier way to find support</div>
            <h1>Find schemes that fit.<br /><span>Just by talking.</span></h1>
            <p className="hero-description">
              Tell SchemeSage a little about yourself. Explore government schemes,
              understand why they may fit, and get a clear checklist for what to do next.
            </p>
            <div className="hero-actions">
              <button className="button button-primary button-large" type="button" onClick={() => navigate("/language")}>
                Try now <ArrowRight size={17} />
              </button>
              <span className="hero-no-login"><CheckCircle2 size={15} /> No sign-up. No login.</span>
            </div>
            <div className="hero-language-hint">
              <Globe2 size={15} />
              <span>Talk in the language you feel at home in</span>
              <span className="hint-dots">· · ·</span>
            </div>
          </div>
          <HeroIllustration onTryNow={() => navigate("/language")} />
          <div className="hero-bottom">
            <span>DESIGNED AROUND YOU</span>
            <div><span>Speak or type</span><i /> <span>One question at a time</span><i /> <span>Clear next steps</span></div>
          </div>
        </section>

        <section className="how-section page-shell" id="how-it-works">
          <div className="section-intro">
            <p className="eyebrow">A SIMPLE, HUMAN PROCESS</p>
            <h2>Three small steps.<br />A little more clarity.</h2>
            <p>No confusing forms. Just a conversation, a few thoughtful questions and a useful place to start.</p>
          </div>
          <div className="steps-grid">
            <StepCard number="01" icon={<AudioLines size={18} />} title="Tell us about you">
              Share details like your age, work and district. Speak or type—whatever feels comfortable.
              <div className="mini-profile">
                <div><span>Occupation</span><strong>Farmer</strong></div>
                <div><span>District</span><strong>East Godavari</strong></div>
                <div><span>Income</span><strong>Kept private</strong></div>
              </div>
            </StepCard>
            <StepCard number="02" icon={<Sparkles size={18} />} title="Explore schemes that fit">
              See possible matches and why they may apply. You choose which ones you want to explore.
              <div className="mini-match">
                <div><span className="mini-match-icon sage">✳</span><span><b>Farm household support</b><small>Possible match</small></span><span className="mini-match-tag">REVIEW</span></div>
                <div><span className="mini-match-icon peach">▤</span><span><b>Education assistance</b><small>Check the criteria</small></span><span className="mini-match-tag">REVIEW</span></div>
              </div>
            </StepCard>
            <StepCard number="03" icon={<FileCheck2 size={18} />} title="Leave with next steps">
              Get an easy-to-follow document checklist and practical application guidance.
              <div className="mini-docs">
                <span><Check size={12} /> Income certificate</span>
                <span><Check size={12} /> Proof of residence</span>
                <span><Check size={12} /> Application steps</span>
              </div>
            </StepCard>
          </div>
        </section>

        <section className="language-preview page-shell" id="languages">
          <div className="language-preview-top">
            <div>
              <p className="eyebrow">YOUR VOICE, YOUR LANGUAGE</p>
              <h2>Speak the way<br />you think.</h2>
              <p>Choose from 10 languages to get started. You can change your choice before the conversation.</p>
            </div>
            <div className="language-orbit" aria-hidden="true">
              <span>नमस्ते</span><span>Hello</span><span>నమస్కారం</span><span>வணக்கம்</span>
              <div><Globe2 size={36} /></div>
            </div>
          </div>
          <button className="button button-outline" type="button" onClick={() => navigate("/language")}>
            Choose your language <ArrowRight size={15} />
          </button>
        </section>

        <section className="privacy-section page-shell" id="privacy">
          <div className="privacy-heading">
            <p className="eyebrow">RESPECTFUL BY DESIGN</p>
            <h2>Helpful, not intrusive.</h2>
            <p>The questions focus on what may help identify relevant schemes.</p>
          </div>
          <div className="privacy-columns">
            <div className="privacy-list">
              <h3><span className="privacy-marker marker-green"><Check size={12} /></span>What we may ask</h3>
              <p>Age and gender</p><p>Occupation and district</p><p>Annual income and relevant scheme criteria</p>
            </div>
            <div className="privacy-list">
              <h3><span className="privacy-marker marker-orange"><X size={11} /></span>What we never ask</h3>
              <p>Aadhaar number</p><p>Phone number</p><p>Bank account details</p>
            </div>
          </div>
        </section>

        <section className="closing-cta page-shell">
          <div className="closing-decoration" aria-hidden="true"><Leaf size={220} strokeWidth={.65} /></div>
          <div>
            <p className="eyebrow">YOUR NEXT STEP CAN START HERE</p>
            <h2>A little conversation.<br />A clearer path forward.</h2>
            <p>Start exploring scheme information with SchemeSage.</p>
          </div>
          <button className="button button-primary button-large" type="button" onClick={() => navigate("/language")}>
            Try now <ArrowRight size={17} />
          </button>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

function StepCard({ number, icon, title, children }: { number: string; icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <article className="step-card">
      <div className="step-top"><span>{number}</span><i /><span className="step-icon">{icon}</span></div>
      <h3>{title}</h3>
      <div className="step-card-description">{children}</div>
    </article>
  );
}

function HeroIllustration({ onTryNow }: { onTryNow: () => void }) {
  return (
    <div className="hero-art" aria-label="SchemeSage voice assistant illustration">
      <div className="hero-orbit hero-orbit-one" /><div className="hero-orbit hero-orbit-two" />
      <div className="hero-glow" />
      <article className="floating-scheme floating-scheme-one">
        <div className="floating-meta"><span>✳</span> FARMING</div>
        <h3>Farm household support</h3><p>Support for eligible families</p>
        <span className="pill pill-sage"><i /> Possible match</span>
      </article>
      <article className="floating-scheme floating-scheme-two">
        <div className="floating-meta"><span>▤</span> EDUCATION</div>
        <h3>Student assistance</h3><p>Help for students and families</p>
        <span className="pill pill-peach"><i /> Explore criteria</span>
      </article>
      <button className="voice-orb" type="button" onClick={onTryNow} aria-label="Try SchemeSage and choose a language">
        <div className="voice-orb-icon"><Mic size={37} strokeWidth={1.55} /></div>
        <span>TRY A CONVERSATION</span>
      </button>
      <article className="floating-note note-one"><span><AudioLines size={17} /></span><div><b>Tell us about you</b><small>Age, work and location</small></div></article>
      <article className="floating-note note-two"><span><FileCheck2 size={17} /></span><div><b>Your next steps</b><small>A checklist you can follow</small></div></article>
      <div className="art-caption">A FRIENDLY VOICE, RIGHT BESIDE YOU</div>
    </div>
  );
}

function LanguagePage() {
  const navigate = useNavigate();
  const savedLanguage = useMemo(() => readSavedLanguage(), []);
  const [selected, setSelected] = useState<AppLanguage | null>(savedLanguage);

  function continueToChat() {
    if (!selected) return;
    try {
      window.localStorage.setItem(LANGUAGE_STORAGE_KEY, JSON.stringify(selected));
    } catch (error) {
      console.error("Unable to save language preference.", error);
    }
    navigate("/conversation", { state: { language: selected } });
  }

  return (
    <main className="flow-page language-page">
      <FlowHeader step="01" label="LANGUAGE" />
      <section className="language-picker panel">
        <Link className="back-link" to="/"><ArrowLeft size={15} /> Back to SchemeSage</Link>
        <div className="language-picker-heading">
          <div className="eyebrow"><Globe2 size={14} /> START WITH WHAT FEELS FAMILIAR</div>
          <h1>Which language<br />would you like to speak?</h1>
          <p>Your assistant will speak and write in your selected language.</p>
        </div>
        <div className="language-options" role="group" aria-label="Choose a language">
          {languages.map((language) => (
            <button
              className={`language-option ${selected?.locale === language.locale ? "language-option-selected" : ""}`}
              type="button"
              key={language.locale}
              aria-pressed={selected?.locale === language.locale}
              onClick={() => setSelected(language)}
            >
              <span className="language-native" lang={language.script}>{language.nativeName}</span>
              <span className="language-option-name">{language.name}</span>
              <span className="language-option-check"><Check size={14} /></span>
            </button>
          ))}
        </div>
        <div className="language-picker-footer">
          <span><LockKeyhole size={14} /> Your language choice stays on this device.</span>
          <button className="button button-primary" type="button" disabled={!selected} onClick={continueToChat}>
            Start conversation <ArrowRight size={16} />
          </button>
        </div>
      </section>
      <p className="flow-footnote">You can speak, type, or switch between both.</p>
    </main>
  );
}

function FlowHeader({ step, label }: { step: string; label: string }) {
  return (
    <header className="flow-header">
      <Brand />
      <div className="flow-progress"><span>STEP {step}</span><i /><span>{label}</span></div>
      <Link className="flow-close" to="/" aria-label="Return home"><X size={18} /></Link>
    </header>
  );
}

function ConversationPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const stateLanguage = (location.state as { language?: AppLanguage } | null)?.language;
  const language = stateLanguage ?? readSavedLanguage();
  if (!language) return <Navigate to="/language" replace />;

  return <ConversationExperience key={language.locale} language={language} navigate={navigate} />;
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

async function readEventStream(
  response: Response,
  onStatus: (status: string) => void,
): Promise<TurnResponse> {
  if (!response.ok) {
    const body = await response.json().catch(() => ({})) as { detail?: string };
    throw new Error(body.detail || `Request failed (${response.status}).`);
  }
  if (!response.body) throw new Error("The server did not provide a response stream.");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let reply: TurnResponse | null = null;

  function consume(block: string) {
    let eventName = "message";
    const data: string[] = [];
    for (const line of block.split(/\r?\n/)) {
      if (line.startsWith("event:")) eventName = line.slice(6).trim();
      if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
    }
    if (eventName === "status" && data.length) {
      onStatus((JSON.parse(data.join("\n")) as { status: string }).status);
    } else if (eventName === "error" && data.length) {
      throw new Error((JSON.parse(data.join("\n")) as { message: string }).message);
    } else if (eventName === "reply" && data.length) {
      reply = JSON.parse(data.join("\n")) as TurnResponse;
    }
  }

  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const blocks = buffer.split(/\r?\n\r?\n/);
    buffer = blocks.pop() ?? "";
    for (const block of blocks) consume(block);
    if (done) break;
  }
  if (buffer.trim()) consume(buffer);
  if (!reply) throw new Error("The server closed the stream without a reply.");
  return reply;
}

function makeAudioUrl(encoded: string | null | undefined): string | undefined {
  if (!encoded) return undefined;
  const binary = window.atob(encoded);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return URL.createObjectURL(new Blob([bytes], { type: "audio/wav" }));
}

const profileFieldMap: Array<{ key: string; field: ProfileField }> = [
  { key: "age", field: "age" },
  { key: "gender", field: "gender" },
  { key: "occupation", field: "occupation" },
  { key: "district", field: "district" },
  { key: "annual_income", field: "income" },
];

const optionalProfileLabels: Record<string, string> = {
  land_acres: "Land (acres)",
  caste_category: "Caste category",
  household_size: "Household members",
  student_course: "Student course",
  disability_status: "Disability relevance",
};

function ConversationExperience({ language, navigate }: { language: AppLanguage; navigate: ReturnType<typeof useNavigate> }) {
  const copy = getConversationCopy(language);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [consented, setConsented] = useState(false);
  const [listening, setListening] = useState(false);
  const [speechNotice, setSpeechNotice] = useState("");
  const [stage, setStage] = useState<TurnResponse["stage"]>("language");
  const [statusText, setStatusText] = useState("Connecting to SchemeSage…");
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const [sessionId, setSessionId] = useState("");
  const [details, setDetails] = useState<TurnResponse["details"] | null>(null);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const audioUrlsRef = useRef<string[]>([]);
  const sessionIdRef = useRef("");
  const initializationRef = useRef<Promise<{ sessionId: string; turn: TurnResponse }> | null>(null);
  const retryRequestRef = useRef<{
    message: ChatMessage;
    request: (id: string) => Promise<Response>;
  } | null>(null);
  const mountedRef = useRef(false);
  const chatContentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const content = chatContentRef.current;
    if (content) content.scrollTo({ top: content.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    let active = true;
    mountedRef.current = true;
    if (!consented) {
      return () => {
        active = false;
        mountedRef.current = false;
      };
    }
    if (!initializationRef.current) {
      initializationRef.current = (async () => {
        const created = await fetch(`${API_BASE_URL}/api/sessions`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ accepted: true, notice_version: PRIVACY_NOTICE_VERSION }),
        });
        if (!created.ok) throw new Error(`Could not create a conversation (${created.status}).`);
        const createdSession = await created.json() as { session_id: string };
        sessionIdRef.current = createdSession.session_id;
        const response = await fetch(
          `${API_BASE_URL}/api/sessions/${createdSession.session_id}/language`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ language: language.name }),
          },
        );
        const turn = await readEventStream(response, (status) => {
          if (mountedRef.current) setStatusText(status.replaceAll("_", " "));
        });
        return { sessionId: createdSession.session_id, turn };
      })();
    }

    initializationRef.current.then(({ sessionId: id, turn }) => {
      if (!active) return;
      setSessionId(id);
      updateFromTurn(turn);
      setLoading(false);
    }).catch((error: unknown) => {
      if (!active) return;
      initializationRef.current = null;
      if (sessionIdRef.current) {
        const orphanedSession = sessionIdRef.current;
        sessionIdRef.current = "";
        void fetch(`${API_BASE_URL}/api/sessions/${orphanedSession}`, {
          method: "DELETE",
          keepalive: true,
        }).catch(() => undefined);
      }
      setSpeechNotice(getRequestError(error));
      setLoading(false);
    });

    return () => {
      active = false;
      mountedRef.current = false;
      if (recorderRef.current?.state === "recording") {
        recorderRef.current.onstop = null;
        recorderRef.current.stop();
      }
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current = null;
      }
      if (sessionIdRef.current) {
        void fetch(`${API_BASE_URL}/api/sessions/${sessionIdRef.current}`, {
          method: "DELETE",
          keepalive: true,
        }).catch((error: unknown) => console.error("Could not delete conversation session.", error));
      }
    };
  }, [connectionAttempt, consented, language.name]);

  useEffect(() => () => {
    audioUrlsRef.current.forEach((url) => URL.revokeObjectURL(url));
    window.speechSynthesis?.cancel();
  }, []);

  function updateFromTurn(turn: TurnResponse) {
    setStage(turn.stage);
    setDetails(turn.details);
    const isSelection = turn.stage === "selection";
    const kind: ChatMessage["kind"] = turn.stage === "complete" ? "checklist" : undefined;
    const audioUrl = makeAudioUrl(turn.audio_base64);
    if (audioUrl) audioUrlsRef.current.push(audioUrl);
    const message: ChatMessage = {
      id: crypto.randomUUID(),
      role: "assistant",
      text: isSelection && turn.details.ranked_schemes
        ? `${turn.reply}\n\n${turn.details.ranked_schemes}`
        : turn.reply,
      kind: kind === "checklist" ? kind : undefined,
      audioUrl,
    };
    setMessages((previous) => [...previous, message]);
    if (voiceEnabled) playAudio(message);
  }

  function speakTextFallback(message: ChatMessage) {
    if (!("speechSynthesis" in window)) {
      setSpeechNotice("Automatic speech is unavailable in this browser. The reply text is still available.");
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message.text);
    utterance.lang = language.locale;
    utterance.onstart = () => setSpeechNotice("");
    utterance.onerror = () => {
      setSpeechNotice("Automatic speech could not start. The reply text is still available.");
    };
    try {
      window.speechSynthesis.speak(utterance);
    } catch {
      setSpeechNotice("Automatic speech could not start. The reply text is still available.");
    }
  }

  function playAudio(message: ChatMessage) {
    if (!message.audioUrl) {
      speakTextFallback(message);
      return;
    }
    audioRef.current?.pause();
    window.speechSynthesis?.cancel();
    const audio = new Audio(message.audioUrl);
    audioRef.current = audio;
    audio.onerror = () => {
      speakTextFallback(message);
    };
    void audio.play().catch(() => {
      audio.onerror = null;
      speakTextFallback(message);
    });
  }

  async function sendTurn(
    userMessage: ChatMessage,
    request: (id: string) => Promise<Response>,
  ) {
    if (!sessionId || loading || stage === "complete") return;
    if (!retryRequestRef.current || retryRequestRef.current.message.id !== userMessage.id) {
      setMessages((previous) => [...previous, userMessage]);
    }
    setLoading(true);
    setSpeechNotice("");
    setStatusText(copy.thinking);
    try {
      const response = await request(sessionId);
      const turn = await readEventStream(response, setStatusText);
      if (turn.transcript) {
        setMessages((previous) => previous.map((message) =>
          message.id === userMessage.id ? { ...message, text: turn.transcript! } : message,
        ));
      }
      updateFromTurn(turn);
      retryRequestRef.current = null;
    } catch (error) {
      retryRequestRef.current = { message: userMessage, request };
      setSpeechNotice(getRequestError(error));
    } finally {
      setLoading(false);
      setStatusText("");
    }
  }

  function handleUserAnswer(value: string) {
    const text = value.trim();
    if (!text || loading || stage === "complete") return;
    setAnswer("");
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    void sendTurn(userMessage, (id) => fetch(`${API_BASE_URL}/api/sessions/${id}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    }));
  }

  async function uploadRecording(blob: Blob) {
    if (!blob.size) {
      setSpeechNotice("No audio was recorded. Try again or type your answer.");
      return;
    }
    const extension = blob.type.includes("mp4") ? "mp4" : blob.type.includes("ogg") ? "ogg" : "webm";
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text: "Voice message" };
    await sendTurn(userMessage, (id) => {
      const formData = new FormData();
      formData.append("audio", blob, `recording.${extension}`);
      return fetch(`${API_BASE_URL}/api/sessions/${id}/audio`, {
        method: "POST",
        body: formData,
      });
    });
  }

  async function startRecording() {
    if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
      setSpeechNotice("Audio recording is not supported in this browser. You can type your answer.");
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const preferredType = ["audio/webm;codecs=opus", "audio/mp4", "audio/webm"]
        .find((type) => MediaRecorder.isTypeSupported(type));
      const recorder = preferredType
        ? new MediaRecorder(stream, { mimeType: preferredType })
        : new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size) chunks.push(event.data);
      };
      recorder.onstop = () => {
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        recorderRef.current = null;
        setListening(false);
        if (mountedRef.current) {
          void uploadRecording(new Blob(chunks, { type: recorder.mimeType || "audio/webm" }));
        }
      };
      recorder.onerror = () => {
        stream.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
        recorderRef.current = null;
        setListening(false);
        setSpeechNotice("The recording failed. Please try again or type your answer.");
      };
      recorderRef.current = recorder;
      recorder.start();
      setListening(true);
      setSpeechNotice("Listening… select the microphone again to send your recording.");
    } catch (error) {
      mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
      recorderRef.current = null;
      setListening(false);
      const name = error instanceof DOMException ? error.name : "";
      setSpeechNotice(name === "NotAllowedError" || name === "SecurityError"
        ? "Microphone permission was denied. Allow microphone access in your browser settings, or type your answer."
        : name === "NotFoundError"
          ? "No microphone was found. Connect one or type your answer."
          : "Could not start microphone recording. Please try again or type your answer.");
    }
  }

  function stopRecording() {
    if (recorderRef.current?.state === "recording") {
      recorderRef.current.stop();
      setSpeechNotice("");
    }
  }

  async function deleteConversation() {
    if (!sessionId) {
      navigate("/");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}`, {
        method: "DELETE",
      });
      if (!response.ok) throw new Error("The conversation could not be deleted. Please try again.");
      sessionIdRef.current = "";
      setSessionId("");
      navigate("/");
    } catch (error) {
      setSpeechNotice(getRequestError(error));
    }
  }

  function retryConnection() {
    initializationRef.current = null;
    setSpeechNotice("");
    setLoading(true);
    setStatusText("Connecting to SchemeSage…");
    setConnectionAttempt((attempt) => attempt + 1);
  }

  function retryLastTurn() {
    const retry = retryRequestRef.current;
    if (retry) {
      void sendTurn(retry.message, retry.request);
    } else {
      retryConnection();
    }
  }

  function toggleVoice() {
    setVoiceEnabled((enabled) => {
      if (enabled) {
        audioRef.current?.pause();
        window.speechSynthesis?.cancel();
      }
      return !enabled;
    });
  }

  const canType = !loading && stage !== "complete" && Boolean(sessionId);
  const stageProgress = stage === "language" ? 0 : stage === "intake" ? 34 : stage === "selection" ? 68 : 100;
  const currentStatus = loading ? (statusText || copy.thinking) : "Ready to help";
  const profile = details?.profile ?? {};

  return (
    <main className="flow-page conversation-page">
      <FlowHeader step="02" label="YOUR CONVERSATION" />
      <div className="conversation-layout">
        <aside className="conversation-rail">
          <div className="rail-title">YOUR JOURNEY</div>
          <div className={`journey-step ${stage === "intake" ? "journey-step-active" : ""}`}><span>1</span><div><b>Tell us about you</b><small>Just a few details</small></div></div>
          <div className={`journey-step ${stage === "selection" ? "journey-step-active" : ""}`}><span>2</span><div><b>Explore schemes</b><small>Review possible matches</small></div></div>
          <div className={`journey-step ${stage === "complete" ? "journey-step-active" : ""}`}><span>3</span><div><b>Your checklist</b><small>Plan what comes next</small></div></div>
          <div className="rail-note"><ShieldCheck size={16} /><span>We never ask for Aadhaar, phone or bank details.</span></div>
        </aside>

        <section className="chat-panel" aria-label="SchemeSage conversation">
          <div className="chat-header">
            <div className="assistant-avatar"><Sparkles size={16} /></div>
            <div className="chat-title"><strong>SchemeSage</strong><span><i /> {currentStatus}</span></div>
            <div className="chat-header-actions">
              <span className="language-chip" lang={language.script}>{language.nativeName}</span>
              <button className="icon-button" type="button" aria-label="Change language" onClick={() => navigate("/language")}><Globe2 size={16} /></button>
              {consented && <button className="icon-button" type="button" aria-label="End and delete conversation" title="End and delete conversation" onClick={() => void deleteConversation()}><Trash2 size={15} /></button>}
            </div>
          </div>
          <div className="conversation-progress"><span style={{ width: `${stageProgress}%` }} /></div>
          {!consented ? (
            <div className="privacy-consent" role="region" aria-labelledby="consent-title">
              <div className="privacy-consent-icon"><LockKeyhole size={20} /></div>
              <h1 id="consent-title">Your information, your choice</h1>
              <p>To suggest schemes, SchemeSage processes details you choose to share, which may include income, caste category, or disability relevance. Extra details are optional, and you can skip any question. Your conversation is stored in the configured database and expires after 24 hours of inactivity by default. You can end the session sooner using “End and delete”.</p>
              <p>If you use voice, your recording is sent to Gnani for transcription. Conversation text is processed by the configured AI provider. Tavily receives scheme names only when checking public scheme information; your personal details are not sent to web search.</p>
              <p>Share only what you are comfortable sharing. You may type instead of using the microphone, and you can stop at any time. This prototype is not an official government service or legal advice.</p>
              <button className="button button-primary" type="button" onClick={() => {
                setSpeechNotice("");
                setLoading(true);
                setStatusText("Connecting to SchemeSage…");
                setConsented(true);
              }}>
                I understand and agree <ArrowRight size={15} />
              </button>
            </div>
          ) : <div className="chat-content" aria-live="polite" ref={chatContentRef}>
            {messages.length === 0 && <div className="chat-date">STARTING A PRIVATE CONVERSATION</div>}
            {messages.map((message) => (
              <div className={`message-row message-row-${message.role}`} key={message.id}>
                {message.role === "assistant" && <div className="message-avatar"><Sparkles size={13} /></div>}
                <div className={`message-bubble message-${message.role}`}>
                  <p lang={language.script}>{message.text}</p>
                  {message.kind === "checklist" && (
                    <div className="checklist-card">
                      <div className="checklist-card-title"><FileCheck2 size={16} /><strong>Your document checklist</strong></div>
                      {details?.document_checklist.map((item) => (
                        <div className="checklist-row" key={item.document}>
                          <span><Check size={12} /></span>{item.document}
                          {item.needed_for.length > 0 && <small>For: {item.needed_for.join(", ")}</small>}
                        </div>
                      ))}
                      {details?.scheme_details.flatMap((scheme) =>
                        (scheme.sources ?? []).map((source) => (
                          <a
                            className="checklist-source"
                            href={source}
                            key={`${scheme.scheme}-${source}`}
                            target="_blank"
                            rel="noreferrer"
                          >
                            Official source for {scheme.scheme}
                          </a>
                        )),
                      )}
                      <small>Confirm current requirements with the official scheme source.</small>
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message-row message-row-assistant" role="status" aria-live="polite">
                <div className="message-avatar"><Sparkles size={13} /></div>
                <div className="message-bubble message-assistant loading-bubble"><LoaderCircle size={15} className="spin" aria-hidden="true" /><span>{statusText || copy.thinking}</span><span className="typing-dots" aria-hidden="true"><i /><i /><i /></span></div>
              </div>
            )}
          </div>}
          {consented && speechNotice && <div className="speech-notice" role="status"><CircleHelp size={14} />{speechNotice}{(!sessionId || retryRequestRef.current) && !loading && <button className="speech-retry" type="button" onClick={retryLastTurn}>Retry</button>}<button type="button" aria-label="Dismiss message" onClick={() => setSpeechNotice("")}><X size={13} /></button></div>}
          {consented && canType ? (
            <form className="composer" onSubmit={(event) => { event.preventDefault(); handleUserAnswer(answer); }}>
              <input value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder={listening ? "Listening… speak now" : "Type your answer here…"} aria-label="Your answer" disabled={loading || listening} />
              <button className={`composer-mic ${listening ? "composer-mic-active" : ""}`} type="button" aria-label={listening ? "Stop and send recording" : "Record your answer"} onClick={listening ? stopRecording : startRecording} disabled={loading && !listening}>
                {listening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button className="composer-send" type="submit" disabled={!answer.trim() || loading} aria-label="Send answer"><Send size={17} /></button>
            </form>
          ) : consented && stage === "complete" ? (
            <div className="conversation-done"><CheckCircle2 size={16} /><span>Your checklist is ready.</span><button type="button" onClick={() => void deleteConversation()}>Finish & delete</button></div>
          ) : null}
          {consented && <div className="chat-disclaimer"><LockKeyhole size={11} /> Your conversation is stored securely and expires automatically.</div>}
        </section>

        <aside className="profile-panel">
          <div className="profile-header"><span>YOUR DETAILS</span><span className="profile-secure"><LockKeyhole size={12} /> PRIVATE</span></div>
          <div className="profile-details-scroll">
            {profileFieldMap.map(({ key, field }) => {
              const value = profile[key];
              return (
                <div className={`profile-field ${value !== null && value !== undefined ? "profile-field-filled" : ""}`} key={key}>
                  <span>{copy.fields[field]}</span><strong>{value ?? "Not yet shared"}</strong>
                  {value !== null && value !== undefined && <Check size={13} />}
                </div>
              );
            })}
            {Object.entries(optionalProfileLabels).map(([key, label]) => {
              const value = profile[key];
              return value === null || value === undefined ? null : (
                <div className="profile-field profile-field-filled" key={key}>
                  <span>{label}</span><strong>{value}</strong><Check size={13} />
                </div>
              );
            })}
          </div>
          <div className="profile-aside-note"><ShieldCheck size={14} /><span>Only share what you're comfortable sharing.</span></div>
          <button className={`voice-toggle ${voiceEnabled ? "voice-toggle-on" : ""}`} type="button" onClick={toggleVoice}>
            <span>{voiceEnabled ? <Volume2 size={15} /> : <MicOff size={15} />}</span>
            <span><b>Spoken replies</b><small>{voiceEnabled ? "Replies are spoken automatically" : "Audio playback off"}</small></span>
            <span className="toggle-track"><i /></span>
          </button>
        </aside>
      </div>
      <p className="flow-footnote conversation-footnote">No login required. Your session expires automatically; use “End and delete” to erase it sooner.</p>
    </main>
  );
}

export default function App() {
  const location = useLocation();

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: "instant" });
  }, [location.pathname]);

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/language" element={<LanguagePage />} />
      <Route path="/conversation" element={<ConversationPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

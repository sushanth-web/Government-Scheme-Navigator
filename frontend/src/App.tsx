import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  ArrowRight,
  AudioLines,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  FileCheck2,
  Globe2,
  Headphones,
  Leaf,
  LoaderCircle,
  LockKeyhole,
  Menu,
  Mic,
  MicOff,
  Pause,
  Send,
  ShieldCheck,
  Sparkles,
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
import { getConversationCopy, demoDocuments, demoSchemes, profileFields } from "./data/conversation";
import { languages } from "./data/languages";
import type {
  AppLanguage,
  ChatMessage,
  ProfileField,
  SpeechRecognition,
  SpeechRecognitionEvent,
} from "./types";

const LANGUAGE_STORAGE_KEY = "schemesage-language";

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

function ConversationExperience({ language, navigate }: { language: AppLanguage; navigate: ReturnType<typeof useNavigate> }) {
  const copy = getConversationCopy(language);
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: "welcome", role: "assistant", text: copy.welcome },
  ]);
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [speakingId, setSpeakingId] = useState<string | null>(null);
  const [speechNotice, setSpeechNotice] = useState("");
  const [stepIndex, setStepIndex] = useState(0);
  const [profile, setProfile] = useState<Partial<Record<ProfileField, string>>>({});
  const [selectedSchemes, setSelectedSchemes] = useState<string[]>([]);
  const [completed, setCompleted] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const speechSupported = typeof window !== "undefined" && "speechSynthesis" in window;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  useEffect(() => () => {
    recognitionRef.current?.stop();
    window.speechSynthesis?.cancel();
  }, []);

  function speakMessage(message: ChatMessage) {
    if (!speechSupported || message.role !== "assistant") {
      setSpeechNotice(copy.speechUnavailable);
      return;
    }
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(message.text);
    utterance.lang = language.locale;
    utterance.rate = 0.94;
    utterance.onstart = () => setSpeakingId(message.id);
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => {
      setSpeakingId(null);
      setSpeechNotice(copy.speechUnavailable);
    };
    window.speechSynthesis.speak(utterance);
    setSpeechNotice("");
  }

  useEffect(() => {
    if (voiceEnabled && speechSupported) speakMessage(messages[0]);
  }, []);

  function addAssistantMessage(text: string, kind?: ChatMessage["kind"]) {
    const message = { id: crypto.randomUUID(), role: "assistant" as const, text, kind };
    setMessages((previous) => [...previous, message]);
    if (voiceEnabled) speakMessage(message);
  }

  function handleUserAnswer(value: string) {
    const text = value.trim();
    if (!text || loading || completed || stepIndex >= profileFields.length) return;

    const field = profileFields[stepIndex];
    const userMessage: ChatMessage = { id: crypto.randomUUID(), role: "user", text };
    const nextProfile = { ...profile, [field]: text };
    setProfile(nextProfile);
    setMessages((previous) => [...previous, userMessage]);
    setAnswer("");
    setLoading(true);

    window.setTimeout(() => {
      const nextStep = stepIndex + 1;
      setStepIndex(nextStep);
      setLoading(false);
      addAssistantMessage(nextStep < profileFields.length ? copy.questions[field] : copy.questions.income, nextStep === profileFields.length ? "schemes" : undefined);
    }, 900);
  }

  function startListening() {
    const Recognition = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!Recognition) {
      setSpeechNotice(copy.voiceUnsupported);
      return;
    }

    recognitionRef.current?.stop();
    const recognition = new Recognition();
    recognition.lang = language.locale;
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const transcript = Array.from({ length: event.results.length }, (_, index) => event.results[index][0].transcript).join("");
      setAnswer(transcript);
    };
    recognition.onerror = (event) => {
      setListening(false);
      setSpeechNotice(event.error === "not-allowed" ? "Allow microphone access to answer by voice." : copy.voiceUnsupported);
    };
    recognition.onend = () => {
      setListening(false);
      recognitionRef.current = null;
    };
    recognitionRef.current = recognition;
    setListening(true);
    setSpeechNotice("");
    recognition.start();
  }

  function stopListening() {
    recognitionRef.current?.stop();
    setListening(false);
  }

  function toggleScheme(id: string) {
    setSelectedSchemes((previous) => previous.includes(id) ? previous.filter((item) => item !== id) : [...previous, id]);
  }

  function buildChecklist() {
    if (selectedSchemes.length === 0) return;
    setLoading(true);
    window.setTimeout(() => {
      setLoading(false);
      setCompleted(true);
      addAssistantMessage(copy.checklist, "checklist");
    }, 1000);
  }

  const canType = !loading && !completed && stepIndex < profileFields.length;

  return (
    <main className="flow-page conversation-page">
      <FlowHeader step="02" label="YOUR CONVERSATION" />
      <div className="conversation-layout">
        <aside className="conversation-rail">
          <div className="rail-title">YOUR JOURNEY</div>
          <div className="journey-step journey-step-active"><span>1</span><div><b>Tell us about you</b><small>Just a few details</small></div></div>
          <div className={`journey-step ${stepIndex >= profileFields.length ? "journey-step-active" : ""}`}><span>2</span><div><b>Explore schemes</b><small>Review possible matches</small></div></div>
          <div className={`journey-step ${completed ? "journey-step-active" : ""}`}><span>3</span><div><b>Your checklist</b><small>Plan what comes next</small></div></div>
          <div className="rail-note"><ShieldCheck size={16} /><span>We never ask for Aadhaar, phone or bank details.</span></div>
        </aside>

        <section className="chat-panel" aria-label="SchemeSage conversation">
          <div className="chat-header">
            <div className="assistant-avatar"><Sparkles size={16} /></div>
            <div className="chat-title"><strong>SchemeSage</strong><span><i /> Ready to help</span></div>
            <div className="chat-header-actions">
              <span className="language-chip" lang={language.script}>{language.nativeName}</span>
              <button className="icon-button" type="button" aria-label="Change language" onClick={() => navigate("/language")}><Globe2 size={16} /></button>
            </div>
          </div>
          <div className="conversation-progress"><span style={{ width: `${Math.min((stepIndex / profileFields.length) * 100, 100)}%` }} /></div>
          <div className="chat-content">
            <div className="chat-date">A NEW CONVERSATION</div>
            {messages.map((message) => (
              <div className={`message-row message-row-${message.role}`} key={message.id}>
                {message.role === "assistant" && <div className="message-avatar"><Sparkles size={13} /></div>}
                <div className={`message-bubble message-${message.role}`}>
                  <p lang={language.script}>{message.text}</p>
                  {message.kind === "schemes" && (
                    <div className="scheme-choices">
                      <p className="choice-helper">{copy.matches}</p>
                      {demoSchemes.map((scheme) => {
                        const chosen = selectedSchemes.includes(scheme.id);
                        return (
                          <button type="button" className={`scheme-choice scheme-choice-${scheme.tone} ${chosen ? "scheme-choice-selected" : ""}`} key={scheme.id} onClick={() => toggleScheme(scheme.id)} aria-pressed={chosen}>
                            <span className="choice-icon">{scheme.icon}</span>
                            <span className="choice-copy"><strong>{scheme.name}</strong><small>{scheme.note}</small></span>
                            <span className="choice-select">{chosen ? <Check size={14} /> : "+"}</span>
                          </button>
                        );
                      })}
                      <button className="button button-primary checklist-cta" type="button" disabled={!selectedSchemes.length || loading} onClick={buildChecklist}>
                        {copy.checklistButton} <ArrowRight size={14} />
                      </button>
                    </div>
                  )}
                  {message.kind === "checklist" && (
                    <div className="checklist-card">
                      <div className="checklist-card-title"><FileCheck2 size={16} /><strong>Your sample checklist</strong></div>
                      {demoDocuments.map((document) => <div className="checklist-row" key={document}><span><Check size={12} /></span>{document}<ChevronRight size={13} /></div>)}
                      <small>Illustrative only · Confirm official requirements</small>
                    </div>
                  )}
                  {message.role === "assistant" && (
                    <button className={`message-audio ${speakingId === message.id ? "message-audio-playing" : ""}`} type="button" onClick={() => speakingId === message.id ? window.speechSynthesis.cancel() : speakMessage(message)} aria-label={speakingId === message.id ? "Stop spoken reply" : "Play spoken reply"}>
                      {speakingId === message.id ? <Pause size={12} /> : <Volume2 size={12} />}
                      {speakingId === message.id ? "Speaking" : "Listen"}
                    </button>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="message-row message-row-assistant">
                <div className="message-avatar"><Sparkles size={13} /></div>
                <div className="message-bubble message-assistant loading-bubble"><LoaderCircle size={15} className="spin" /><span>{stepIndex >= profileFields.length ? copy.thinking : copy.thinking}</span><span className="typing-dots"><i /><i /><i /></span></div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
          {speechNotice && <div className="speech-notice" role="status"><CircleHelp size={14} />{speechNotice}<button type="button" aria-label="Dismiss message" onClick={() => setSpeechNotice("")}><X size={13} /></button></div>}
          {!speechSupported && voiceEnabled && <div className="speech-notice speech-notice-soft" role="status"><Headphones size={14} />{copy.speechUnavailable}<button type="button" aria-label="Dismiss message" onClick={() => setVoiceEnabled(false)}><X size={13} /></button></div>}
          {canType ? (
            <form className="composer" onSubmit={(event) => { event.preventDefault(); handleUserAnswer(answer); }}>
              <input value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder={listening ? "Listening… speak now" : "Type your answer here…"} aria-label="Your answer" disabled={loading} />
              <button className={`composer-mic ${listening ? "composer-mic-active" : ""}`} type="button" aria-label={listening ? "Stop voice input" : "Speak your answer"} onClick={listening ? stopListening : startListening}>
                {listening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
              <button className="composer-send" type="submit" disabled={!answer.trim() || loading} aria-label="Send answer"><Send size={17} /></button>
            </form>
          ) : (
            <div className="conversation-done"><CheckCircle2 size={16} /><span>{completed ? "Your sample checklist is ready." : "Choose one or more example schemes above to continue."}</span>{completed && <button type="button" onClick={() => navigate("/")}>Finish</button>}</div>
          )}
          <div className="chat-disclaimer"><LockKeyhole size={11} /> Demo experience — not connected to live eligibility or scheme data.</div>
        </section>

        <aside className="profile-panel">
          <div className="profile-header"><span>YOUR DETAILS</span><span className="profile-secure"><LockKeyhole size={12} /> PRIVATE</span></div>
          {profileFields.map((field) => (
            <div className={`profile-field ${profile[field] ? "profile-field-filled" : ""}`} key={field}>
              <span>{copy.fields[field]}</span><strong>{profile[field] ?? "Not yet shared"}</strong>
              {profile[field] && <Check size={13} />}
            </div>
          ))}
          <div className="profile-aside-note"><ShieldCheck size={14} /><span>Only share what you're comfortable sharing.</span></div>
          <button className={`voice-toggle ${voiceEnabled ? "voice-toggle-on" : ""}`} type="button" onClick={() => setVoiceEnabled((enabled) => !enabled)}>
            <span>{voiceEnabled ? <Volume2 size={15} /> : <MicOff size={15} />}</span>
            <span><b>Spoken replies</b><small>{voiceEnabled ? "On in this browser" : "Turned off"}</small></span>
            <span className="toggle-track"><i /></span>
          </button>
        </aside>
      </div>
      <p className="flow-footnote conversation-footnote">Your responses stay in this demo session. A real deployment needs a secure backend.</p>
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

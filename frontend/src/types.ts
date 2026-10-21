export interface AppLanguage {
  name: string;
  nativeName: string;
  locale: string;
  script: string;
}

export interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  text: string;
  kind?: "checklist";
  audioUrl?: string;
}

export type ProfileField = "age" | "gender" | "occupation" | "district" | "income";

export interface SchemeChecklistDetails {
  scheme: string;
  documents: Array<{ name: string; note?: string }>;
  sources?: string[];
  web_search_status?: string;
  start_date?: string;
  deadline?: string;
  dates_source?: string;
  how_to_apply?: string[];
  other_requirements?: string[];
  where_to_apply?: string;
}

export interface ConversationDetails {
  profile: Record<string, string | number | null>;
  ranked_schemes: string | null;
  selected_schemes: string[];
  scheme_details: SchemeChecklistDetails[];
  document_checklist: Array<{ document: string; needed_for: string[] }>;
  language: string | null;
  locale: string | null;
}

export interface TurnResponse {
  session_id: string;
  stage: "language" | "intake" | "selection" | "complete";
  reply: string;
  details: ConversationDetails;
  audio_base64?: string | null;
  audio_error?: string | null;
  transcript?: string;
}

export interface SpeechRecognitionAlternative {
  transcript: string;
}

export interface SpeechRecognitionResult {
  readonly isFinal: boolean;
  readonly length: number;
  [index: number]: SpeechRecognitionAlternative;
}

export interface SpeechRecognitionResultList {
  readonly length: number;
  [index: number]: SpeechRecognitionResult;
}

export interface SpeechRecognitionEvent extends Event {
  readonly resultIndex: number;
  readonly results: SpeechRecognitionResultList;
}

export interface SpeechRecognitionErrorEvent extends Event {
  readonly error: string;
}

export interface SpeechRecognition extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onerror: ((event: SpeechRecognitionErrorEvent) => void) | null;
  onend: (() => void) | null;
  start(): void;
  stop(): void;
}

export interface SpeechRecognitionConstructor {
  new (): SpeechRecognition;
}

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

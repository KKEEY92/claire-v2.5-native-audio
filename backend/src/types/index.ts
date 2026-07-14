export type AppView = 'call' | 'auratone' | 'analytics' | 'monitor';

/** Strukturiertes Live-Event aus dem Agenten (Datenkanal) für den Monitor-Feed. */
export interface LogEntry {
  ts: number;
  level: string;   // info | tool | energy | warn | error
  source: string;  // greeting | stt | llm | tts | memory | aura | system
  text: string;
}

/** Eine Transkript-Zeile (Du / Claire) im Live-Monitor. */
export interface TranscriptLine {
  ts: number;
  role: string;    // "user" | "assistant"
  text: string;
}

import { useEffect, useMemo, useRef, useState } from 'react';
import { useEmotionStore } from '../../stores/emotionStore';
import type { LogEntry } from '../../types';

function fmtTime(ts: number): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString('de-DE', { hour12: false });
}

function fmtSession(total: number): string {
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

const LEVEL_COLOR: Record<string, string> = {
  info: 'text-sky-300',
  tool: 'text-violet-300',
  energy: 'text-amber-300',
  warn: 'text-orange-300',
  error: 'text-red-400',
};

function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) {
    return <div className="h-10 flex items-center text-white/30 text-xs">…sammle Energie-Verlauf</div>;
  }
  const w = 220, h = 40;
  const pts = values
    .map((v, i) => {
      const x = (i / (values.length - 1)) * w;
      const y = h - Math.max(0, Math.min(1, v)) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline points={pts} fill="none" stroke="var(--energy-color)" strokeWidth="2" />
    </svg>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-white/40 text-[10px] tracking-wider">{label}</span>
      <span className="text-lg font-light text-white">{value}</span>
    </div>
  );
}

export function LiveMonitorView() {
  const {
    energy, moodTag, factsCount, turnCount, sessionSeconds,
    llmProvider, vadActive, energyHistory, events, transcript,
  } = useEmotionStore();

  const [tab, setTab] = useState<'events' | 'raw'>('events');
  const [rawLines, setRawLines] = useState<string[]>([]);
  const feedRef = useRef<HTMLDivElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);

  // Raw stdout via SSE (log_server.py über Vite-Proxy /logs)
  useEffect(() => {
    if (tab !== 'raw') return;
    setRawLines((l) => (l.length ? l : ['… verbinde mit /logs (log_server.py)']));
    const es = new EventSource('/logs');
    const onMsg = (e: MessageEvent) =>
      setRawLines((l) => [...l, e.data].slice(-500));
    es.onmessage = onMsg;
    es.addEventListener('hello', onMsg as EventListener);
    es.onerror = () =>
      setRawLines((l) => [...l, '⚠️ /logs nicht erreichbar — läuft log_server.py auf dem Host?'].slice(-500));
    return () => es.close();
  }, [tab]);

  // Auto-Scroll
  useEffect(() => { feedRef.current?.scrollTo(0, feedRef.current.scrollHeight); }, [events, rawLines, tab]);
  useEffect(() => { transcriptRef.current?.scrollTo(0, transcriptRef.current.scrollHeight); }, [transcript]);

  const providerLabel = llmProvider === 'lmstudio' ? 'LM Studio (lokal)' : llmProvider === 'google' ? 'Gemini (Cloud)' : '—';
  const pct = Math.round(Math.max(0, Math.min(1, energy)) * 100);
  const eventsView = useMemo(() => events.slice(-300), [events]);

  return (
    <div className="w-full h-full flex flex-col gap-4 relative z-10 p-6 pt-20 max-w-5xl mx-auto">
      <h2 className="text-xl font-light tracking-[0.2em] uppercase text-white/80">Live Monitor</h2>

      {/* Metadaten-Header */}
      <div className="glass p-5 rounded-2xl flex flex-wrap items-center gap-x-8 gap-y-4 font-mono">
        <div className="flex flex-col gap-1 min-w-[240px]">
          <span className="text-white/40 text-[10px] tracking-wider">ENERGIE · {moodTag ?? '—'} · {pct}%</span>
          <div className="h-2 w-full bg-white/10 rounded-full overflow-hidden">
            <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'var(--energy-color)' }} />
          </div>
          <Sparkline values={energyHistory} />
        </div>
        <Stat label="FACTS" value={factsCount} />
        <Stat label="TURNS" value={turnCount} />
        <Stat label="SESSION" value={fmtSession(sessionSeconds)} />
        <Stat label="LLM" value={<span className="text-sm">{providerLabel}</span>} />
        <Stat label="VAD" value={<span className={vadActive ? 'text-emerald-300' : 'text-white/40'}>{vadActive ? 'Silero ✓' : 'STT-Endpointing'}</span>} />
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Live-Transkript */}
        <div className="glass rounded-2xl p-4 w-2/5 flex flex-col min-h-0">
          <span className="text-white/40 text-[10px] tracking-wider mb-2">TRANSKRIPT</span>
          <div ref={transcriptRef} className="flex-1 overflow-y-auto flex flex-col gap-2 pr-1">
            {transcript.length === 0 && <span className="text-white/30 text-sm">…noch keine Sprache</span>}
            {transcript.map((t, i) => (
              <div key={i} className={`text-sm leading-snug ${t.role === 'user' ? 'text-white/90' : 'text-[var(--energy-color)]'}`}>
                <span className="text-white/40 text-xs mr-2">{t.role === 'user' ? 'Du' : 'Claire'}</span>
                {t.text}
              </div>
            ))}
          </div>
        </div>

        {/* Terminal-Feed */}
        <div className="glass rounded-2xl p-4 flex-1 flex flex-col min-h-0">
          <div className="flex gap-2 mb-2">
            {(['events', 'raw'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`text-[10px] tracking-wider px-3 py-1 rounded-full ${tab === t ? 'bg-white/15 text-white' : 'text-white/40'}`}
              >
                {t === 'events' ? 'EVENTS (Datenkanal)' : 'RAW STDOUT'}
              </button>
            ))}
          </div>
          <div ref={feedRef} className="flex-1 overflow-y-auto font-mono text-xs leading-relaxed bg-black/30 rounded-lg p-3">
            {tab === 'events' ? (
              eventsView.length === 0 ? (
                <span className="text-white/30">…warte auf Events (Greeting, Tool-Calls, Energie-Shifts)</span>
              ) : (
                eventsView.map((e: LogEntry, i) => (
                  <div key={i} className="whitespace-pre-wrap">
                    <span className="text-white/30">{fmtTime(e.ts)} </span>
                    <span className="text-white/40">[{e.source}] </span>
                    <span className={LEVEL_COLOR[e.level] ?? 'text-white/80'}>{e.text}</span>
                  </div>
                ))
              )
            ) : (
              rawLines.map((l, i) => (
                <div key={i} className="whitespace-pre-wrap text-white/75">{l}</div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

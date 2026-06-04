import { useState, useEffect } from 'react';
import { MoodGlow } from './components/Dashboard/MoodGlow';
import { PhoneCallScreen } from './components/PhoneCall/PhoneCallScreen';
import { AuraToneView } from './components/AuraTone/AuraToneView';
import { AnalyticsView } from './components/Analytics/AnalyticsView';
import { useLiveKit } from './hooks/useLiveKit';
import type { AppView } from './types';

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL ?? '';
const TOKEN_ENDPOINT = import.meta.env.VITE_LIVEKIT_TOKEN_ENDPOINT ?? '';

export default function App() {
  const [view, setView] = useState<AppView>('call');
  const [active, setActive] = useState(false);
  const [token, setToken] = useState('');

  // FIX: Token dynamisch holen
  useEffect(() => {
    if (!active || !TOKEN_ENDPOINT) return;
    fetch(`${TOKEN_ENDPOINT}?room=claire&identity=user-${Date.now()}`)
      .then(r => r.json())
      .then(d => setToken(d.token))
      .catch(e => console.error('Token fetch failed', e));
  }, [active]);

  useLiveKit({ serverUrl: LIVEKIT_URL, token, enabled: active && !!token });

  return (
    <div className="relative w-screen h-dvh overflow-hidden bg-[#08080f]">
      <MoodGlow />
      <nav className="absolute top-4 left-1/2 -translate-x-1/2 z-50 glass rounded-full px-4 py-2 flex gap-6">
        {(['call', 'auratone', 'analytics'] as AppView[]).map((v) => (
          <button key={v} onClick={() => setView(v)} className="text-xs font-mono tracking-widest uppercase cursor-pointer transition-colors"
            style={{ color: view === v ? 'var(--energy-color)' : '#64748b' }}>
            {v === 'call' ? '📞 CALL' : v === 'auratone' ? '🎛️ AURA' : '📊 DATA'}
          </button>
        ))}
      </nav>
      <main className="relative z-10 w-full h-full">
        {view === 'call' && <PhoneCallScreen onEndCall={() => setActive(false)} />}
        {view === 'auratone' && <AuraToneView />}
        {view === 'analytics' && <AnalyticsView />}
      </main>
      {!active && view === 'call' && (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <button onClick={() => setActive(true)} className="px-8 py-4 rounded-full font-mono text-sm tracking-widest border cursor-pointer hover:bg-purple-500/20 transition-colors"
            style={{ background: 'rgba(168,85,247,0.1)', borderColor: 'rgba(168,85,247,0.4)', color: '#a855f7' }}>
            CLAIRE VERBINDEN
          </button>
        </div>
      )}
    </div>
  );
}

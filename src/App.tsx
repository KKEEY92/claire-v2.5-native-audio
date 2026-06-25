import { useState } from 'react';
import { MoodGlow } from './components/Dashboard/MoodGlow';
import { PhoneCallScreen } from './components/PhoneCall/PhoneCallScreen';
import { AuraToneView } from './components/AuraTone/AuraToneView';
import { AnalyticsView } from './components/Analytics/AnalyticsView';
import { LiveMonitorView } from './components/Monitor/LiveMonitorView';
import { useLiveKit } from './hooks/useLiveKit';
import { useEmotionStore } from './stores/emotionStore';
import type { AppView } from './types';

const LIVEKIT_URL = import.meta.env.VITE_LIVEKIT_URL ?? '';

export default function App() {
  const [view, setView] = useState<AppView>('call');
  const [sessionActive, setSessionActive] = useState(false);
  const requestConnection = useEmotionStore((s) => s.requestConnection);

  useLiveKit({ serverUrl: LIVEKIT_URL, sessionActive });

  const handleStartCall = () => {
    setSessionActive(true);
    requestConnection();
  };

  const handleEndCall = () => {
    setSessionActive(false);
    useEmotionStore.getState().resetConnection();
  };

  const handleRetry = () => {
    if (!sessionActive) setSessionActive(true);
    useEmotionStore.getState().retryConnection();
  };

  return (
    <div className="relative w-screen h-dvh overflow-hidden bg-[#08080f]">
      <MoodGlow />
      <nav className="absolute top-0 left-0 right-0 z-50 safe-top">
        <div className="flex justify-center px-3 pt-2 pb-1">
          <div className="glass rounded-full px-3 py-1.5 flex gap-1 sm:gap-4">
            {(['call', 'auratone', 'analytics', 'monitor'] as AppView[]).map((v) => (
              <button
                key={v}
                type="button"
                onClick={() => setView(v)}
                className="text-[10px] sm:text-xs font-mono tracking-wider sm:tracking-widest uppercase cursor-pointer transition-colors px-2 py-1.5 rounded-full min-w-[44px] min-h-[44px] flex items-center justify-center"
                style={{
                  color: view === v ? 'var(--energy-color)' : '#64748b',
                  background: view === v ? 'rgba(168,85,247,0.1)' : 'transparent',
                }}
              >
                {v === 'call' ? 'CALL' : v === 'auratone' ? 'AURA' : v === 'analytics' ? 'DATA' : 'LIVE'}
              </button>
            ))}
          </div>
        </div>
      </nav>
      <main className="relative z-10 w-full h-full">
        {view === 'call' && (
          <PhoneCallScreen onEndCall={handleEndCall} onRetry={handleRetry} />
        )}
        {view === 'auratone' && <AuraToneView />}
        {view === 'analytics' && <AnalyticsView />}
        {view === 'monitor' && <LiveMonitorView />}
      </main>
      {!sessionActive && view === 'call' && (
        <div className="absolute inset-0 z-20 flex items-center justify-center">
          <button
            type="button"
            onClick={handleStartCall}
            className="px-8 py-4 rounded-full font-mono text-sm tracking-widest border cursor-pointer hover:bg-purple-500/20 transition-colors min-h-[48px]"
            style={{
              background: 'rgba(168,85,247,0.1)',
              borderColor: 'rgba(168,85,247,0.4)',
              color: '#a855f7',
            }}
          >
            CLAIRE VERBINDEN
          </button>
        </div>
      )}
    </div>
  );
}
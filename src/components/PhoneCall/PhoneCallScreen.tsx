import { FFTAnalyzer } from './FFTAnalyzer';
import { NeonRing } from './NeonRing';
import { disconnect } from '../../hooks/useLiveKit';
import { useEmotionStore, type ConnectionState } from '../../stores/emotionStore';

const STATUS_LABELS: Record<ConnectionState, string> = {
  idle: 'Bereit',
  token_fetch: 'Verbinde…',
  connecting: 'Starte…',
  connected: 'Verbunden',
  error: 'Fehler',
};

export function PhoneCallScreen({
  onEndCall,
  onRetry,
}: {
  onEndCall: () => void;
  onRetry: () => void;
}) {
  const { connectionState, moodTag, isConnected } = useEmotionStore();

  const statusLabel =
    connectionState === 'connected'
      ? moodTag || STATUS_LABELS.connected
      : STATUS_LABELS[connectionState];

  const handleHangUp = () => {
    disconnect();
    onEndCall();
  };

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-12 relative z-10">
      <div className="text-center">
        <h2 className="text-2xl font-light tracking-[0.2em] uppercase text-white/80">Claire</h2>
        <p
          aria-live="polite"
          className="text-sm text-white/40 font-mono tracking-wider uppercase mt-2"
        >
          {statusLabel}
        </p>
        {connectionState === 'error' && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-4 px-5 py-2 rounded-full font-mono text-xs tracking-widest border border-cyan-400/40 text-cyan-300 hover:bg-cyan-500/10 transition-colors cursor-pointer"
          >
            Erneut verbinden
          </button>
        )}
      </div>

      <NeonRing />

      <div className="h-20 flex items-center justify-center">
        {isConnected && connectionState === 'connected' && <FFTAnalyzer />}
      </div>

      <button
        type="button"
        onClick={handleHangUp}
        className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-500 hover:bg-red-500/20 transition-colors cursor-pointer"
        aria-label="Anruf beenden"
      >
        <span className="text-2xl rotate-[135deg]">📞</span>
      </button>
    </div>
  );
}
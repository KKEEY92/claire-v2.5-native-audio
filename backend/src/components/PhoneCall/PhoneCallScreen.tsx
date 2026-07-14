import { useEffect, useRef } from 'react';
import { NeonRing } from './NeonRing';
import { disconnect, getAgentAnalyser } from '../../hooks/useLiveKit';
import { useEmotionStore, type ConnectionState } from '../../stores/emotionStore';

const STATUS_LABELS: Record<ConnectionState, string> = {
  idle: 'Bereit',
  token_fetch: 'Verbinde…',
  connecting: 'Starte…',
  connected: 'Verbunden',
  error: 'Fehler',
};

const BAR_COUNT = 32;
const CANVAS_WIDTH = 280;
const CANVAS_HEIGHT = 60;

export function PhoneCallScreen({
  onEndCall,
  onRetry,
}: {
  onEndCall: () => void;
  onRetry: () => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef(0);
  const { connectionState, moodTag, isConnected, modeConfig } = useEmotionStore();

  const statusLabel =
    connectionState === 'connected'
      ? moodTag || STATUS_LABELS.connected
      : STATUS_LABELS[connectionState];

  const showVisualizer = isConnected && connectionState === 'connected';

  useEffect(() => {
    if (!showVisualizer) return;

    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    if (!ctx.roundRect) {
      ctx.roundRect = (x: number, y: number, w: number, h: number, r: number) => {
        ctx.beginPath();
        ctx.moveTo(x + r, y);
        ctx.lineTo(x + w - r, y);
        ctx.quadraticCurveTo(x + w, y, x + w, y + r);
        ctx.lineTo(x + w, y + h - r);
        ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
        ctx.lineTo(x + r, y + h);
        ctx.quadraticCurveTo(x, y + h, x, y + h - r);
        ctx.lineTo(x, y + r);
        ctx.quadraticCurveTo(x, y, x + r, y);
        ctx.closePath();
      };
    }

    const barW = CANVAS_WIDTH / BAR_COUNT - 2;
    const dataArray = new Uint8Array(128);

    const draw = () => {
      const analyser = getAgentAnalyser();
      ctx.clearRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

      if (analyser) {
        analyser.getByteFrequencyData(dataArray);
      } else {
        dataArray.fill(0);
      }

      for (let i = 0; i < BAR_COUNT; i++) {
        const bin = Math.floor((i / BAR_COUNT) * dataArray.length);
        const amplitude = dataArray[bin] / 255;
        const h = Math.max(2, amplitude * CANVAS_HEIGHT * 0.92);
        const x = i * (barW + 2);
        const y = (CANVAS_HEIGHT - h) / 2;

        ctx.fillStyle = modeConfig.color;
        ctx.globalAlpha = analyser ? 0.35 + amplitude * 0.65 : 0.2;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, h, 2);
        ctx.fill();
      }

      ctx.globalAlpha = 1;
      animRef.current = requestAnimationFrame(draw);
    };

    animRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(animRef.current);
  }, [showVisualizer, modeConfig.color]);

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
        {showVisualizer && (
          <canvas
            ref={canvasRef}
            width={CANVAS_WIDTH}
            height={CANVAS_HEIGHT}
            className="opacity-80"
            aria-hidden
          />
        )}
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
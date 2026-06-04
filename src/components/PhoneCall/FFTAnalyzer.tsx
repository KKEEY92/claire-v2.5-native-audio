import { useEffect, useRef } from 'react';
import { useEmotionStore } from '../../stores/emotionStore';

export function FFTAnalyzer() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animRef = useRef<number>(0);
  const { modeConfig, isSpeaking } = useEmotionStore();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    
    // FIX: Schneller Fallback für fehlendes ctx.roundRect (Safari)
    if (!ctx.roundRect) {
      (ctx as any).roundRect = (x: number, y: number, w: number, h: number, r: number) => {
        ctx.fillRect(x, y, w, h);
      };
    }

    const bars = 32; const barW = canvas.width / bars - 2; let frame = 0;

    const draw = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      for (let i = 0; i < bars; i++) {
        const amplitude = isSpeaking
          ? 0.2 + 0.8 * Math.abs(Math.sin(frame * 0.05 + i * 0.4) * Math.cos(i * 0.2))
          : 0.05 + 0.08 * Math.abs(Math.sin(frame * 0.02 + i * 0.3));
        const h = amplitude * canvas.height;
        const x = i * (barW + 2);
        const y = (canvas.height - h) / 2;

        ctx.fillStyle = modeConfig.color;
        ctx.globalAlpha = 0.5 + amplitude * 0.5;
        ctx.beginPath();
        ctx.roundRect(x, y, barW, h, 2);
        ctx.fill();
      }
      frame++;
      animRef.current = requestAnimationFrame(draw);
    };

    draw();
    return () => cancelAnimationFrame(animRef.current);
  }, [isSpeaking, modeConfig]);

  return <canvas ref={canvasRef} width={280} height={60} className="opacity-80" />;
}

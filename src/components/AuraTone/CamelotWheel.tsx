import { useEmotionStore } from '../../stores/emotionStore';

export function CamelotWheel() {
  const { modeConfig } = useEmotionStore();
  return (
    <div className="w-80 h-80 rounded-full border border-white/10 relative flex items-center justify-center glass shadow-2xl transition-all duration-1000 ease-in-out"
      style={{ boxShadow: `0 0 40px ${modeConfig.glow}` }}>
      <div className="text-center font-mono text-sm tracking-widest text-white/50">
        Harmonic Field
      </div>
      <div className="absolute inset-4 rounded-full border border-white/5 transition-all duration-1000 ease-in-out" style={{ borderColor: modeConfig.color, opacity: 0.5 }} />
    </div>
  );
}

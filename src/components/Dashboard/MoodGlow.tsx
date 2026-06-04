import { useEmotionStore } from '../../stores/emotionStore';

export function MoodGlow() {
  const { modeConfig } = useEmotionStore();
  return (
    <div className="absolute inset-0 pointer-events-none transition-all duration-1000 ease-in-out"
      style={{
        background: `radial-gradient(circle at 50% 50%, ${modeConfig.glow} 0%, transparent 60%)`,
        opacity: modeConfig.intensity * 0.8
      }}
    />
  );
}

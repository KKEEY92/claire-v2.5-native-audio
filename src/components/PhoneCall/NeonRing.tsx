import { useEmotionStore } from '../../stores/emotionStore';

export function NeonRing() {
  const { modeConfig, isSpeaking } = useEmotionStore();
  return (
    <div className="relative w-48 h-48 sm:w-64 sm:h-64 flex items-center justify-center rounded-full"
      style={{
        boxShadow: `0 0 ${isSpeaking ? 60 : 30}px ${modeConfig.glow}`,
        border: `2px solid ${modeConfig.color}`,
        transition: 'all 0.3s ease-out'
      }}>
      <div className={`w-32 h-32 sm:w-48 sm:h-48 rounded-full opacity-50 ${isSpeaking ? 'animate-pulse' : ''}`}
        style={{ backgroundColor: modeConfig.color, filter: 'blur(40px)' }} />
    </div>
  );
}

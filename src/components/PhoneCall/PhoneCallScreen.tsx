import { FFTAnalyzer } from './FFTAnalyzer';
import { NeonRing } from './NeonRing';
import { useEmotionStore } from '../../stores/emotionStore';

export function PhoneCallScreen({ onEndCall }: { onEndCall: () => void }) {
  const { isConnected, moodTag } = useEmotionStore();
  
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-12 relative z-10">
      <div className="text-center">
        <h2 className="text-2xl font-light tracking-[0.2em] uppercase text-white/80">Claire</h2>
        <p className="text-sm text-white/40 font-mono tracking-wider uppercase mt-2">
          {isConnected ? (moodTag || 'Listening...') : 'Connecting...'}
        </p>
      </div>
      
      <NeonRing />
      
      <div className="h-20 flex items-center justify-center">
        {isConnected && <FFTAnalyzer />}
      </div>
      
      <button onClick={onEndCall} className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center text-red-500 hover:bg-red-500/20 transition-colors cursor-pointer">
        <span className="text-2xl rotate-[135deg]">📞</span>
      </button>
    </div>
  );
}

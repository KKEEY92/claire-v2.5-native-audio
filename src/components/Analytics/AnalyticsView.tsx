import { useEmotionStore } from '../../stores/emotionStore';

function formatSessionSeconds(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

export function AnalyticsView() {
  const { factsCount, turnCount, sessionSeconds } = useEmotionStore();

  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-8 relative z-10 p-8">
      <h2 className="text-xl font-light tracking-[0.2em] uppercase text-white/80">Data Stream</h2>
      <div className="glass p-8 rounded-2xl w-full max-w-2xl">
        <div className="grid grid-cols-3 gap-6 font-mono">
          <div className="flex flex-col gap-2">
            <span className="text-white/50 text-xs">FACTS EXTRACTED</span>
            <span className="text-3xl font-light text-white">{factsCount}</span>
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-white/50 text-xs">SESSION TIME</span>
            <span className="text-3xl font-light text-white">
              {formatSessionSeconds(sessionSeconds)}
            </span>
          </div>
          <div className="flex flex-col gap-2">
            <span className="text-white/50 text-xs">CONVERSATION TURNS</span>
            <span className="text-3xl font-light text-white">{turnCount}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
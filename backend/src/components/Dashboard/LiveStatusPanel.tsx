import { useEmotionStore } from '../../stores/emotionStore';

export function LiveStatusPanel() {
  const { energy, moodTag, isConnected } = useEmotionStore();
  return (
    <div className="glass p-4 rounded-xl flex flex-col gap-2 font-mono text-xs w-64">
      <div className="flex justify-between">
        <span className="text-white/50">STATUS</span>
        <span className={isConnected ? "text-green-400" : "text-yellow-400"}>
          {isConnected ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>
      <div className="flex justify-between">
        <span className="text-white/50">ENERGY</span>
        <span className="text-white/90">{(energy * 100).toFixed(0)}%</span>
      </div>
      <div className="flex justify-between">
        <span className="text-white/50">MOOD</span>
        <span className="text-white/90">{moodTag || 'N/A'}</span>
      </div>
    </div>
  );
}

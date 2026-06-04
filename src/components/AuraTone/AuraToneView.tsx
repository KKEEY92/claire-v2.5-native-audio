import { CamelotWheel } from './CamelotWheel';
import { LiveStatusPanel } from '../Dashboard/LiveStatusPanel';

export function AuraToneView() {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-8 relative z-10 p-8">
      <h2 className="text-xl font-light tracking-[0.2em] uppercase text-white/80">AuraTone Matrix</h2>
      <div className="flex gap-12 items-center">
        <CamelotWheel />
        <LiveStatusPanel />
      </div>
    </div>
  );
}

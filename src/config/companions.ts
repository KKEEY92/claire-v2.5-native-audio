export type EnergyMode = 'calm' | 'default' | 'energetic' | 'intense';
export interface EnergyConfig {
  color: string;
  glow: string;
  intensity: number;
}

export function getEnergyMode(energy: number): EnergyMode {
  if (energy < 0.3) return 'calm';
  if (energy < 0.6) return 'default';
  if (energy < 0.8) return 'energetic';
  return 'intense';
}

export function getEnergyConfig(energy: number): EnergyConfig {
  const mode = getEnergyMode(energy);
  switch (mode) {
    case 'calm': return { color: '#3b82f6', glow: 'rgba(59,130,246,0.5)', intensity: 0.3 };
    case 'default': return { color: '#a855f7', glow: 'rgba(168,85,247,0.5)', intensity: 0.6 };
    case 'energetic': return { color: '#ec4899', glow: 'rgba(236,72,153,0.5)', intensity: 0.8 };
    case 'intense': return { color: '#ef4444', glow: 'rgba(239,68,68,0.5)', intensity: 1.0 };
  }
}

import { create } from 'zustand';
import { getEnergyMode, getEnergyConfig, type EnergyMode, type EnergyConfig } from '../config/companions';

interface EmotionState {
  energy: number;
  mode: EnergyMode;
  modeConfig: EnergyConfig;
  moodTag: string | null;
  factsCount: number;
  isConnected: boolean;
  isSpeaking: boolean;

  setEnergy: (energy: number) => void;
  setMoodTag: (tag: string | null) => void;
  setFacts: (count: number) => void;
  setConnected: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
}

export const useEmotionStore = create<EmotionState>((set) => ({
  energy: 0.65, mode: 'default', modeConfig: getEnergyConfig(0.65),
  moodTag: null, factsCount: 0, isConnected: false, isSpeaking: false,
  setEnergy: (energy) => set({ energy, mode: getEnergyMode(energy), modeConfig: getEnergyConfig(energy) }),
  setMoodTag: (tag) => set({ moodTag: tag }),
  setFacts: (count) => set({ factsCount: count }),
  setConnected: (v) => set({ isConnected: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),
}));

import { create } from 'zustand';
import { getEnergyMode, getEnergyConfig, type EnergyMode, type EnergyConfig } from '../config/companions';

export type ConnectionState =
  | 'idle'
  | 'token_fetch'
  | 'connecting'
  | 'connected'
  | 'error';

interface EmotionState {
  energy: number;
  mode: EnergyMode;
  modeConfig: EnergyConfig;
  moodTag: string | null;
  factsCount: number;
  isConnected: boolean;
  isSpeaking: boolean;
  connectionState: ConnectionState;
  connectNonce: number;

  setEnergy: (energy: number) => void;
  setMoodTag: (tag: string | null) => void;
  setFacts: (count: number) => void;
  setConnected: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  setConnectionState: (state: ConnectionState) => void;
  requestConnection: () => void;
  retryConnection: () => void;
  resetConnection: () => void;
}

export const useEmotionStore = create<EmotionState>((set) => ({
  energy: 0.65,
  mode: 'default',
  modeConfig: getEnergyConfig(0.65),
  moodTag: null,
  factsCount: 0,
  isConnected: false,
  isSpeaking: false,
  connectionState: 'idle',
  connectNonce: 0,

  setEnergy: (energy) =>
    set({ energy, mode: getEnergyMode(energy), modeConfig: getEnergyConfig(energy) }),
  setMoodTag: (tag) => set({ moodTag: tag }),
  setFacts: (count) => set({ factsCount: count }),
  setConnected: (v) => set({ isConnected: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),
  setConnectionState: (state) => set({ connectionState: state }),

  requestConnection: () =>
    set((s) => ({
      connectionState: 'token_fetch',
      connectNonce: s.connectNonce + 1,
      isConnected: false,
      isSpeaking: false,
    })),

  retryConnection: () =>
    set((s) => ({
      connectionState: 'idle',
      connectNonce: s.connectNonce + 1,
      isConnected: false,
      isSpeaking: false,
    })),

  resetConnection: () =>
    set({
      connectionState: 'idle',
      isConnected: false,
      isSpeaking: false,
    }),
}));
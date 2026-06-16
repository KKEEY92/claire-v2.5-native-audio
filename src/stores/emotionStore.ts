import { create } from 'zustand';
import { getEnergyMode, getEnergyConfig, type EnergyMode, type EnergyConfig } from '../config/companions';
import type { LogEntry, TranscriptLine } from '../types';

const EVENTS_CAP = 300;
const TRANSCRIPT_CAP = 100;
const ENERGY_HISTORY_CAP = 60;

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
  turnCount: number;
  sessionSeconds: number;
  isConnected: boolean;
  isSpeaking: boolean;
  connectionState: ConnectionState;
  connectNonce: number;

  // ── Live-Monitor ──────────────────────────────────────────────
  llmProvider: string | null;       // "lmstudio" | "google"
  vadActive: boolean;
  energyHistory: number[];          // Ringpuffer für Sparkline
  events: LogEntry[];               // Datenkanal-Event-Feed
  transcript: TranscriptLine[];     // Du + Claire

  setEnergy: (energy: number) => void;
  setMoodTag: (tag: string | null) => void;
  setFacts: (count: number) => void;
  setTurnCount: (count: number) => void;
  setSessionSeconds: (seconds: number) => void;
  setConnected: (v: boolean) => void;
  setSpeaking: (v: boolean) => void;
  setConnectionState: (state: ConnectionState) => void;
  setRuntimeInfo: (info: { llmProvider?: string; vadActive?: boolean }) => void;
  pushEvent: (e: LogEntry) => void;
  pushTranscript: (t: TranscriptLine) => void;
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
  turnCount: 0,
  sessionSeconds: 0,
  isConnected: false,
  isSpeaking: false,
  connectionState: 'idle',
  connectNonce: 0,

  llmProvider: null,
  vadActive: false,
  energyHistory: [],
  events: [],
  transcript: [],

  setEnergy: (energy) =>
    set((s) => ({
      energy,
      mode: getEnergyMode(energy),
      modeConfig: getEnergyConfig(energy),
      energyHistory: [...s.energyHistory, energy].slice(-ENERGY_HISTORY_CAP),
    })),
  setMoodTag: (tag) => set({ moodTag: tag }),
  setFacts: (count) => set({ factsCount: count }),
  setTurnCount: (count) => set({ turnCount: count }),
  setSessionSeconds: (seconds) => set({ sessionSeconds: seconds }),
  setConnected: (v) => set({ isConnected: v }),
  setSpeaking: (v) => set({ isSpeaking: v }),
  setConnectionState: (state) => set({ connectionState: state }),
  setRuntimeInfo: (info) =>
    set((s) => ({
      llmProvider: info.llmProvider ?? s.llmProvider,
      vadActive: info.vadActive ?? s.vadActive,
    })),
  pushEvent: (e) => set((s) => ({ events: [...s.events, e].slice(-EVENTS_CAP) })),
  pushTranscript: (t) =>
    set((s) => ({ transcript: [...s.transcript, t].slice(-TRANSCRIPT_CAP) })),

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
      factsCount: 0,
      turnCount: 0,
      sessionSeconds: 0,
      events: [],
      transcript: [],
      energyHistory: [],
    }),
}));
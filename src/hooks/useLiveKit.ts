import { useEffect, useRef } from 'react';
import { Room, RoomEvent, Track, type RemoteTrack } from 'livekit-client';
import { useEmotionStore } from '../stores/emotionStore';

const TOKEN_ENDPOINT =
  import.meta.env.VITE_LIVEKIT_TOKEN_ENDPOINT ?? '/token';

const INITIAL_ENERGY = 0.65;

/** Shared session refs so hang-up can tear down outside the hook instance. */
const session = {
  room: null as Room | null,
  audioElements: [] as HTMLMediaElement[],
  connectGeneration: 0,
};

let audioContext: AudioContext | null = null;
let agentAnalyser: AnalyserNode | null = null;
let agentMediaSource: MediaStreamAudioSourceNode | null = null;

function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
  if (audioContext.state === 'suspended') {
    void audioContext.resume();
  }
  return audioContext;
}

/**
 * Visualizer-Analyser für Claires Remote-Audio.
 *
 * WICHTIG: Claires Stimme wird vom <audio>-Element (track.attach()) NATIV
 * abgespielt — wir fassen das Element NICHT an. createMediaElementSource ist für
 * Remote-WebRTC-Streams in Chrome kaputt (kapert das Element → kein Ton UND keine
 * Analyser-Daten). Stattdessen analysieren wir den Track direkt über
 * createMediaStreamSource (das funktioniert für WebRTC-Audio) und verbinden den
 * Analyser NICHT mit destination (sonst doppelte Wiedergabe).
 */
function setupAgentAudioAnalyser(track: RemoteTrack): void {
  const ctx = getAudioContext();
  try {
    if (agentMediaSource) {
      agentMediaSource.disconnect();
      agentMediaSource = null;
    }
    if (agentAnalyser) {
      agentAnalyser.disconnect();
      agentAnalyser = null;
    }

    const stream = new MediaStream([track.mediaStreamTrack]);
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 256;
    source.connect(analyser);
    // KEIN analyser.connect(destination): die Stimme läuft über das <audio>-Element.

    agentMediaSource = source;
    agentAnalyser = analyser;
  } catch (err) {
    // Visualizer ist optional — Claires Stimme spielt unabhängig davon nativ.
    console.error('[useLiveKit] Visualizer-Analyser fehlgeschlagen (Stimme unberührt):', err);
  }
}

function cleanupAudioAnalysis(): void {
  agentAnalyser = null;
  if (agentMediaSource) {
    try {
      agentMediaSource.disconnect();
    } catch {
      /* already disconnected */
    }
    agentMediaSource = null;
  }
  if (audioContext) {
    const ctx = audioContext;
    audioContext = null;
    void ctx.close().catch(() => {
      /* context may already be closed */
    });
  }
}

/** Returns the analyser wired to Claire's remote audio output, if connected. */
export function getAgentAnalyser(): AnalyserNode | null {
  return agentAnalyser;
}

interface UseLiveKitOptions {
  serverUrl: string;
  /** Session should stay active (user started a call). */
  sessionActive: boolean;
}

function resetStoreToInitial(): void {
  const {
    setEnergy,
    setMoodTag,
    setFacts,
    setTurnCount,
    setSessionSeconds,
    setConnected,
    setSpeaking,
    setConnectionState,
  } = useEmotionStore.getState();
  setEnergy(INITIAL_ENERGY);
  setMoodTag(null);
  setFacts(0);
  setTurnCount(0);
  setSessionSeconds(0);
  setConnected(false);
  setSpeaking(false);
  setConnectionState('idle');
}

function removeRemoteAudioElements(): void {
  session.audioElements.forEach((el) => el.remove());
  session.audioElements.length = 0;
  cleanupAudioAnalysis();
}

async function stopLocalAudioTracks(room: Room): Promise<void> {
  try {
    await room.localParticipant.setMicrophoneEnabled(false);
  } catch {
    /* mic may already be off or room not fully connected */
  }
  room.localParticipant.trackPublications.forEach((publication) => {
    publication.track?.stop();
  });
}

function teardownRoom(): void {
  const room = session.room;
  session.room = null;
  if (!room) {
    removeRemoteAudioElements();
    return;
  }

  void stopLocalAudioTracks(room).finally(() => {
    try {
      room.disconnect(true);
    } catch (err) {
      console.error('[useLiveKit] room.disconnect failed:', err);
    }
    removeRemoteAudioElements();
  });
}

/** Ends the LiveKit session and resets emotion store to initial values. */
export function disconnect(): void {
  session.connectGeneration += 1;
  teardownRoom();
  resetStoreToInitial();
}

async function fetchLiveKitToken(): Promise<string> {
  const url = `${TOKEN_ENDPOINT}?room=claire&identity=user-${Date.now()}`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Token-Server antwortete mit ${res.status}`);
  }
  const data = (await res.json()) as { token?: string };
  if (!data.token) {
    throw new Error('Kein Token in der Antwort');
  }
  return data.token;
}

export function useLiveKit({ serverUrl, sessionActive }: UseLiveKitOptions) {
  const roomRef = useRef<Room | null>(null);
  const connectNonce = useEmotionStore((s) => s.connectNonce);
  const { setConnected, setSpeaking, setConnectionState, resetConnection } = useEmotionStore();

  useEffect(() => {
    if (!sessionActive) {
      session.connectGeneration += 1;
      teardownRoom();
      resetConnection();
      roomRef.current = null;
      return;
    }

    if (!serverUrl) {
      setConnectionState('error');
      return;
    }

    const generation = ++session.connectGeneration;
    let cancelled = false;

    const isStale = () =>
      cancelled || generation !== session.connectGeneration || !sessionActive;

    const cleanupRoom = () => {
      teardownRoom();
      roomRef.current = null;
      setConnected(false);
      setSpeaking(false);
    };

    const run = async () => {
      setConnectionState('token_fetch');

      let token: string;
      try {
        token = await fetchLiveKitToken();
      } catch (err) {
        console.error('[useLiveKit] Token fetch failed:', err);
        if (!isStale()) setConnectionState('error');
        return;
      }

      if (isStale()) return;

      setConnectionState('connecting');

      // Standard-ICE (direkt + Relay-Fallback). Universell für normale Geräte.
      // Hinweis: macOS 27 Beta verbiegt den Browser-WebRTC-UDP-Pfad — dort fließt
      // kein Audio-Medium. Auf stabilen Geräten (Handy/anderer Rechner) klappt es.
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
      });
      session.room = room;
      roomRef.current = room;

      room.on(RoomEvent.Connected, async () => {
        if (isStale()) return;
        try {
          await room.localParticipant.setMicrophoneEnabled(true);
          if (isStale()) return;
          setConnected(true);
          setConnectionState('connected');
        } catch (err) {
          console.error('[useLiveKit] Microphone denied:', err);
          if (!isStale()) {
            setConnectionState('error');
            setConnected(false);
          }
          teardownRoom();
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        if (isStale()) return;
        setConnected(false);
        setSpeaking(false);
        if (useEmotionStore.getState().connectionState === 'connected') {
          setConnectionState('idle');
        }
      });

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          // <audio>-Element spielt Claires Stimme NATIV ab (zuverlässig).
          const audioEl = track.attach();
          audioEl.autoplay = true;
          audioEl.playsInline = true;
          audioEl.style.display = 'none';
          document.body.appendChild(audioEl);
          session.audioElements.push(audioEl);
          // Visualizer separat aus dem Track (nicht aus dem Element).
          setupAgentAudioAnalyser(track as RemoteTrack);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el) => {
            el.remove();
            const idx = session.audioElements.indexOf(el);
            if (idx >= 0) session.audioElements.splice(idx, 1);
          });
          agentAnalyser = null;
          if (agentMediaSource) {
            try {
              agentMediaSource.disconnect();
            } catch {
              /* already disconnected */
            }
            agentMediaSource = null;
          }
        }
      });

      room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
        const isAgentSpeaking = speakers.some((s) => !s.isLocal);
        setSpeaking(isAgentSpeaking);
      });

      room.on(RoomEvent.DataReceived, (data: Uint8Array) => {
        try {
          const payload = JSON.parse(new TextDecoder().decode(data));
          if (payload.type === 'telemetry') {
            const store = useEmotionStore.getState();
            store.setEnergy(payload.energy ?? INITIAL_ENERGY);
            store.setMoodTag(payload.moodTag ?? null);
            if (typeof payload.factsCount === 'number') {
              store.setFacts(payload.factsCount);
            }
            if (typeof payload.turnCount === 'number') {
              store.setTurnCount(payload.turnCount);
            }
            if (typeof payload.sessionSeconds === 'number') {
              store.setSessionSeconds(payload.sessionSeconds);
            }
          }
        } catch {
          /* ignore non-JSON */
        }
      });

      try {
        await room.connect(serverUrl, token);
      } catch (err) {
        console.error('[useLiveKit] room.connect failed:', err);
        if (!isStale()) {
          setConnectionState('error');
          setConnected(false);
        }
        cleanupRoom();
      }
    };

    void run();

    return () => {
      cancelled = true;
      session.connectGeneration += 1;
      cleanupRoom();
    };
  }, [
    sessionActive,
    serverUrl,
    connectNonce,
    setConnected,
    setSpeaking,
    setConnectionState,
    resetConnection,
  ]);

  return { room: roomRef.current, disconnect };
}
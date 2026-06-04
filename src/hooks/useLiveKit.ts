import { useEffect, useRef } from 'react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useEmotionStore } from '../stores/emotionStore';

const TOKEN_ENDPOINT =
  import.meta.env.VITE_LIVEKIT_TOKEN_ENDPOINT ?? '/token';

interface UseLiveKitOptions {
  serverUrl: string;
  /** Session should stay active (user started a call). */
  sessionActive: boolean;
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
  const {
    setConnected,
    setSpeaking,
    setConnectionState,
    resetConnection,
  } = useEmotionStore();

  useEffect(() => {
    if (!sessionActive) {
      roomRef.current?.disconnect();
      roomRef.current = null;
      resetConnection();
      return;
    }

    if (!serverUrl) {
      setConnectionState('error');
      return;
    }

    let cancelled = false;
    const audioElements: HTMLMediaElement[] = [];

    const cleanupRoom = () => {
      roomRef.current?.disconnect();
      roomRef.current = null;
      audioElements.forEach((el) => el.remove());
      audioElements.length = 0;
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
        if (!cancelled) setConnectionState('error');
        return;
      }

      if (cancelled) return;

      setConnectionState('connecting');

      const room = new Room({ adaptiveStream: true, dynacast: true });
      roomRef.current = room;

      room.on(RoomEvent.Connected, async () => {
        if (cancelled) return;
        try {
          await room.localParticipant.setMicrophoneEnabled(true);
          setConnected(true);
          setConnectionState('connected');
        } catch (err) {
          console.error('[useLiveKit] Microphone denied:', err);
          setConnectionState('error');
          setConnected(false);
          room.disconnect();
        }
      });

      room.on(RoomEvent.Disconnected, () => {
        if (cancelled) return;
        setConnected(false);
        setSpeaking(false);
        if (useEmotionStore.getState().connectionState === 'connected') {
          setConnectionState('idle');
        }
      });

      room.on(RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          const audioEl = track.attach();
          audioEl.autoplay = true;
          audioEl.playsInline = true;
          audioEl.style.display = 'none';
          document.body.appendChild(audioEl);
          audioElements.push(audioEl);
        }
      });

      room.on(RoomEvent.TrackUnsubscribed, (track) => {
        if (track.kind === Track.Kind.Audio) {
          track.detach().forEach((el) => {
            el.remove();
            const idx = audioElements.indexOf(el);
            if (idx >= 0) audioElements.splice(idx, 1);
          });
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
            useEmotionStore.getState().setEnergy(payload.energy ?? 0.65);
            useEmotionStore.getState().setMoodTag(payload.moodTag ?? null);
          }
        } catch {
          /* ignore non-JSON */
        }
      });

      try {
        await room.connect(serverUrl, token);
      } catch (err) {
        console.error('[useLiveKit] room.connect failed:', err);
        if (!cancelled) {
          setConnectionState('error');
          setConnected(false);
        }
        cleanupRoom();
      }
    };

    void run();

    return () => {
      cancelled = true;
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

  return { room: roomRef.current };
}
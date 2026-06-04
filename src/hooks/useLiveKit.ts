import { useEffect, useRef, useState } from 'react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useEmotionStore } from '../stores/emotionStore';

interface UseLiveKitOptions { serverUrl: string; token: string; enabled: boolean; }

export function useLiveKit({ serverUrl, token, enabled }: UseLiveKitOptions) {
  const roomRef = useRef<Room | null>(null);
  const [isReady, setIsReady] = useState(false);
  const { setConnected, setSpeaking } = useEmotionStore();

  useEffect(() => {
    if (!enabled || !token || !serverUrl) return;

    const room = new Room({ adaptiveStream: true, dynacast: true });
    roomRef.current = room;

    room.on(RoomEvent.Connected, () => {
      setConnected(true);
      setIsReady(true);
      // Mikrofon aktivieren
      room.localParticipant.setMicrophoneEnabled(true)
        .catch(err => console.error('Failed to enable microphone:', err));
    });
    room.on(RoomEvent.Disconnected, () => { setConnected(false); setIsReady(false); setSpeaking(false); });

    // FIX: Audio an den DOM hängen, sonst bleibt Claire stumm!
    room.on(RoomEvent.TrackSubscribed, (track) => {
      console.log('[useLiveKit] TrackSubscribed:', track.kind, track.sid);
      if (track.kind === Track.Kind.Audio) {
        const audioEl = track.attach();
        audioEl.autoplay = true;
        audioEl.playsInline = true;
        audioEl.style.display = 'none';
        document.body.appendChild(audioEl);
        console.log('[useLiveKit] Attached audio element to DOM:', audioEl);
      }
    });

    room.on(RoomEvent.TrackUnsubscribed, (track) => {
      console.log('[useLiveKit] TrackUnsubscribed:', track.kind, track.sid);
      if (track.kind === Track.Kind.Audio) {
        track.detach().forEach(el => {
          el.remove();
          console.log('[useLiveKit] Removed audio element from DOM:', el);
        });
      }
    });

    // Dynamisch tracken ob Claire gerade spricht
    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      const isAgentSpeaking = speakers.some(s => !s.isLocal);
      setSpeaking(isAgentSpeaking);
    });

    room.on(RoomEvent.DataReceived, (data: Uint8Array) => {
      try {
        const payload = JSON.parse(new TextDecoder().decode(data));
        if (payload.type === 'telemetry') {
          useEmotionStore.getState().setEnergy(payload.energy ?? 0.65);
          useEmotionStore.getState().setMoodTag(payload.moodTag ?? null);
        }
      } catch (_) {}
    });

    room.connect(serverUrl, token).catch(console.error);

    return () => { room.disconnect(); roomRef.current = null; setSpeaking(false); };
  }, [enabled, token, serverUrl]);

  return { room: roomRef.current, isReady };
}

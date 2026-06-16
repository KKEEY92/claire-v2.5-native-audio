# Claire V2 im Container (Linux / Python 3.12 + Silero VAD)

Containerisiert **Agent + Token-Server**, um den Agenten von **macOS 27 Beta +
Python 3.15.0a1** zu entkoppeln. Im Container läuft der stabile `multiprocessing`
PROCESS-Executor (kein 60-s-„unresponsive"-Kill) **und** Silero VAD (echte
Turn-Detection — onnxruntime gibt es nur auf Linux).

## Architektur

```
┌─ Mac (Host) ──────────────────────────────┐      ┌─ Docker ─────────────────┐
│  Browser ──► LiveKit Cloud (WebRTC)        │      │  agent  (python agent.py)│
│  Vite-Frontend :5173                       │      │   ├─ STT/TTS → Google    │
│  LM Studio :1234  ◄───────────────────────────────┤   ├─ LLM → LM Studio     │
│  Google ADC ~/.config/gcloud   ────(mount)────────┤   │     host.docker.intern│
│                                            │      │   └─ Silero VAD          │
│  localhost:3001  ◄────────(port 3001)─────────────┤  token-server            │
└────────────────────────────────────────────┘      └──────────────────────────┘
```

- **LM Studio** bleibt zwingend auf dem Mac (braucht die GPU). Der Agent erreicht
  es über `host.docker.internal:1234`.
- **Frontend + Browser** bleiben nativ. Der Browser verbindet sich selbst mit
  LiveKit Cloud — der Container ist daran nicht beteiligt.

## Voraussetzungen
1. **Docker Desktop** läuft.
2. **LM Studio** läuft, Modell `qwen2.5-7b-instruct` geladen (Context 8192,
   GPU max — siehe Latenz-Hinweis unten), Server auf `:1234`.
3. **Google ADC** vorhanden: `gcloud auth application-default login` →
   `~/.config/gcloud/application_default_credentials.json`.
4. **`.env`** ausgefüllt (aus `.env.example`): `LIVEKIT_URL/API_KEY/API_SECRET`,
   `GOOGLE_CLOUD_PROJECT`, `GOOGLE_GENAI_USE_VERTEXAI=1`, `LMSTUDIO_MODEL`.
   `LIVEKIT_JOB_EXECUTOR` darf gesetzt bleiben — Compose überschreibt es auf `process`.

## Start
```bash
# Agent + Token-Server bauen und starten:
docker compose up --build

# Mac-seitig: NICHT den lokalen token_server.py parallel laufen lassen
# (Port-3001-Konflikt). Frontend wie gewohnt:
npm run dev          # http://localhost:5173 → "Anrufen"
```

## Verifikation
- Agent-Log: `[Worker] Job-Executor: process`, `registered worker`,
  `🤖 [LLM] LOKAL via LM Studio`.
- Beim Verbinden: `[prewarm] Silero VAD geladen`, **keine** `VAD is not set`-Warnung,
  `[Claire] VAD: Silero aktiv`.
- Greeting: `[TTS Node] Started` → `[Claire] Greeting reply sent`, **kein**
  `process is unresponsive`.

## Stop
```bash
docker compose down
```

## Bekannte Punkte
- **Browser-seitige macOS-27-Beta-Effekte** (z.B. WebRTC-Disconnects) behebt der
  Container NICHT — der Browser nutzt den nativen Host-Netzwerk-Stack.
- **WebRTC-UDP aus dem Container:** als ausgehender Client meist ok; bei
  Verbindungsproblemen greift LiveKits TURN/TCP-Fallback.
- **Latenz:** LM Studio mit 128K-Default-Context killt die TTFT. Modell mit
  `lms load qwen2.5-7b-instruct -y --gpu max --context-length 8192` laden.
- **ADC** ist ein User-Refresh-Token; für echtes Cloud-Deploy später auf ein
  Service-Account-JSON umstellen.

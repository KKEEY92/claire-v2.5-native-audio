<div align="center">

<img src="https://img.shields.io/badge/Claire-V2.5_Native_Audio-blueviolet?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Claire V2.5"/>
<img src="https://img.shields.io/badge/Gemini-Native_Audio-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini Native Audio"/>
<img src="https://img.shields.io/badge/Full_Duplex-200ms-00C853?style=for-the-badge" alt="Full Duplex"/>
<img src="https://img.shields.io/badge/EmotionEngine-v2-FF6D00?style=for-the-badge" alt="EmotionEngine"/>
<img src="https://img.shields.io/badge/Memory-SQLite_+_Drive-7C4DFF?style=for-the-badge" alt="Memory"/>

<br/><br/>

**Standalone upgrade von [Claire V2](https://github.com/KKEEY92/claire-v2).**<br/>
Gemini Native Audio ersetzt die komplette STT→LLM→TTS Pipeline.<br/>
Lokales Voice Agent Cockpit mit WebGL-Shader-Engine, EmotionEngine-Gauge und persistenter SQLite-Memory.

</div>

---

## Was ist anders als V2?

| | Claire V2 | Claire V2.5 (Native Audio) |
|---|---|---|
| **Architektur** | Google STT → Gemini LLM → Google TTS (Chirp3-HD) | Gemini Native Audio (alles in einem) |
| **Latenz** | ~800ms (3 API-Calls) | ~200ms (1 Session) |
| **Duplex** | Half-Duplex (abwechselnd) | **Full-Duplex** (gleichzeitig hören + sprechen) |
| **Infrastruktur** | LiveKit + Cloud Run + Docker | **`python launcher.py`** |
| **UI** | — | Voice Agent Cockpit (WebGL Shaders, Waveform, EmotionEngine) |
| **Memory** | Google Drive only | **SQLite-Primary** + Drive als Backup |
| **Start** | npm + Docker + Token-Server | Doppelklick Desktop-Launcher |
| **Stimme** | Google TTS Chirp3-HD | Gemini Neural Voices (Aoede, Kore, etc.) |
| **Prosodie** | TTS-Parameter (rate, gain) | Prompt-gesteuert (natürlicher) |

## Was gleich geblieben ist

- **KKI Persona OS v1.0** — 7-Layer Identity Framework (`persona.py`)
- **EmotionEngine v2** — Energie-Tracking, zirkadiane Rhythmen, Prosodie-Steuerung
- **Tools** — `save_memory`, `recall_memory` mit Embedding-basierter Suche

## Quickstart

```bash
# 1. Clone
git clone https://github.com/KKEEY92/claire-v2.5-native-audio.git
cd claire-v2.5-native-audio

# 2. Venv + Dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements-native.txt

# 3. API Key (https://aistudio.google.com/apikey)
cp .env.native.example .env
# → GOOGLE_API_KEY eintragen

# 4. Dashboard starten
.venv/bin/python launcher.py
# → öffnet http://localhost:8550 automatisch
```

Alternativ: CLI-only ohne Dashboard:
```bash
.venv/bin/python claire.py
```

## Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  launcher.py (Entry Point)                                      │
│  Port 8550 · Preflight: Gemini/LM Studio/Claire_Mix Probes      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │  dashboard.py (FastAPI)                                    │  │
│  │  GET /api/health · /api/memory · /api/sessions · /api/config│  │
│  │  WS  /ws (Audio Bridge)                                    │  │
│  └─────────────┬──────────────────────────────────────────────┘  │
│                │                                                  │
│  ┌─────────────▼──────────────────────────────────────────────┐  │
│  │  Browser Dashboard (static/index.html)                     │  │
│  │  • WebGL Shader Engine (5 Shaders, voice-reactive)         │  │
│  │  • Waveform Visualizer (Mic + Speaker, dual-channel)       │  │
│  │  • EmotionEngine Gauge + Sparkline                         │  │
│  │  • Live Transcript + Memory Panel                          │  │
│  │  • Health Badge (Gemini/LM Studio/Offline)                 │  │
│  │  • AudioWorklet → WebSocket → Gemini ← base64 Audio       │  │
│  └─────────────┬──────────────────────────────────────────────┘  │
│                │                                                  │
│  ┌─────────────▼───────────┐  ┌───────────────────────────────┐  │
│  │  Gemini 2.5 Flash       │  │  memory.py (SQLite-Primary)   │  │
│  │  Native Audio           │  │  ~/.claire_memory/claire.db   │  │
│  │  • Full-Duplex          │  │  • Facts, EgoState, Sessions  │  │
│  │  • Tool Calling         │  │  • Drive Backup (async)       │  │
│  │  • Persona + Prosodie   │  │  • Vertex AI Embeddings       │  │
│  └─────────────────────────┘  └───────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

| Endpoint | Beschreibung |
|----------|-------------|
| `GET /` | Dashboard UI |
| `GET /api/config` | Modell, Voice, Sample Rates |
| `GET /api/health` | Gemini, LM Studio, SQLite, Drive, Claire_Mix Status |
| `GET /api/memory` | Facts gruppiert nach Kategorie |
| `GET /api/sessions` | Session-History (Dauer, Turns, Saves, Energie) |
| `WS /ws` | Bidirektionale Audio-Bridge (Browser ↔ Gemini) |

## Konfiguration (.env)

```env
# Gemini API Key (kostenlos: aistudio.google.com/apikey)
GOOGLE_API_KEY=...

# Modell
CLAIRE_MODEL=gemini-2.5-flash-native-audio-latest

# Stimme: Aoede (Default), Kore, Puck, Charon, Fenrir
CLAIRE_VOICE=Aoede

# Google Cloud (optional, für Memory-Embeddings)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west3

# Google Drive Backup (optional)
GDRIVE_MEMORY_FOLDER_ID=...
```

## Dateien

| Datei | Beschreibung |
|-------|-------------|
| `launcher.py` | Entry Point: Preflight-Checks → Dashboard → Browser |
| `dashboard.py` | FastAPI Backend: API + WebSocket Audio Bridge |
| `static/index.html` | Voice Agent Cockpit (WebGL, Waveform, EmotionEngine) |
| `claire.py` | Standalone CLI Agent (ohne Dashboard) |
| `memory.py` | SQLite-Primary Memory + Drive Backup |
| `persona.py` | KKI Persona OS v1.0 (7 Layers) |
| `agent.py` | Original V2 LiveKit Agent (Referenz) |

## Desktop-Start (macOS)

`~/Desktop/Claire V2.5.command` — Doppelklick öffnet Terminal + Dashboard.

## Verwandte Repos

| Repo | Beschreibung |
|------|-------------|
| [claire-v2](https://github.com/KKEEY92/claire-v2) | Original mit LiveKit Pipeline |
| [Claire-V2-Architecture](https://github.com/KKEEY92/Claire-V2-Architecture) | Architektur-Dokumentation |
| [Aria](https://github.com/KKEEY92/Aria---Your-AI-Companion) | AI Companion mit Gemini Native Audio (React) |
| **claire-v2.5-native-audio** | ← dieses Repo |

## Lizenz

MIT

# CLAUDE.md — Claire V2.5 Native Audio

## Repository Overview

Claire V2.5 is a standalone real-time voice agent powered by Gemini Native Audio. It replaces the multi-API speech pipeline (STT → LLM → TTS) from Claire V2 with a single unified Gemini session, achieving ~200ms latency with full-duplex audio. The agent speaks German, embodies a persistent persona ("Claire"), and maintains long-term memory via Google Drive.

**Author:** Kevin Kuck / KKI
**License:** MIT
**Default Branch:** `main`

## Architecture

### Pipeline Comparison

| Aspect | Claire V2 (LiveKit) | Claire V2.5 (Native Audio) |
|---|---|---|
| Architecture | Google STT → Gemini LLM → Google TTS | Gemini Native Audio (unified) |
| Latency | ~800ms (3 API calls) | ~200ms (1 session) |
| Duplex | Half-duplex | Full-duplex |
| Infrastructure | LiveKit + Cloud Run + Docker | `python claire.py` |
| Voice | Google TTS Chirp3-HD | Gemini Neural Voices (Aoede, Kore, Puck, Charon, Fenrir) |
| Dependencies | ~15 packages + server | 7 packages, no server |

### Core Stack

| Layer | Technology | Purpose |
|---|---|---|
| Voice Agent | Python, `google-genai`, PyAudio | Standalone mic → Gemini → speaker pipeline |
| Persona System | Python (`persona.py`) | 7-layer identity framework (KKI Persona OS v1.0) |
| Memory | Google Drive API, Vertex AI Embeddings | Persistent fact storage, semantic recall |
| EmotionEngine | Python (`persona.py`) | Energy tracking (0.0–1.0), circadian rhythm, mood shifts |
| Frontend | React, Vite, Tailwind, TypeScript | Dashboard, phone-call UI, analytics, monitor views |
| LiveKit Agent (V2) | `agent_telemetry.py`, LiveKit SDK | Original V2 agent (retained for reference) |
| Containerization | Docker, docker-compose | V2 agent + token-server deployment |

## Repository Structure

```
/
├── .agents/
│   ├── rules/                    # Agent behavior rules
│   └── workflows/                # Agent workflow definitions
├── _archive/
│   └── claire-v2-frontend/       # Archived V2 frontend
├── src/                          # Active React frontend
│   ├── components/
│   │   ├── Analytics/            # Analytics dashboard
│   │   ├── AuraTone/             # AuraTone audio integration
│   │   ├── Dashboard/            # Main dashboard
│   │   ├── Monitor/              # Live container log monitor
│   │   └── PhoneCall/            # Phone call UI
│   ├── config/                   # App configuration
│   ├── hooks/                    # Custom React hooks (useLiveKit, etc.)
│   ├── stores/                   # Zustand state management (emotionStore)
│   ├── types/                    # TypeScript type definitions
│   ├── App.tsx                   # Root component with view switching
│   ├── index.css                 # Global styles
│   └── main.tsx                  # Entry point
├── claire.py                     # V2.5 standalone voice agent (main entry)
├── agent.py                      # V2 LiveKit agent (reference)
├── agent_telemetry.py            # V2 agent with telemetry broadcasting
├── persona.py                    # KKI Persona OS — 7-layer identity + EmotionEngine
├── memory.py                     # DriveMemory — persistent facts, semantic search
├── token_server.py               # LiveKit token endpoint (V2)
├── log_server.py                 # Container stdout SSE streaming
├── brain_test.py                 # Persona/memory tests
├── generate_aenderungsbericht.py # Changelog generator
├── generate_debug_report.py      # Debug report generator
├── Dockerfile                    # Python 3.12 agent container
├── docker-compose.yml            # Agent + token-server orchestration
├── requirements.txt              # V2 Python dependencies
├── requirements-native.txt       # V2.5 Python dependencies (7 packages)
├── requirements-docker.txt       # Docker-specific dependencies
├── package.json                  # Frontend dependencies (React, Vite, Tailwind, Zustand)
├── vite.config.ts                # Vite config with proxy + PWA
├── index.html                    # SPA entry HTML
├── AGENTS.md                     # Agent behavior documentation
├── README.md                     # Project documentation
├── DOCKER.md                     # Docker setup guide
├── ZUSTANDSBERICHT_2026-06-04.md # Status report
└── LICENSE                       # MIT
```

## Key Domain Concepts

- **Gemini Native Audio**: Google's unified audio model — handles speech input, language understanding, and voice output in a single streaming session
- **KKI Persona OS v1.0**: 7-layer identity framework (Identity Lock, Persona Core, Life History, Emotional State, Language/Expression, Narrative Engine, Memory Hygiene)
- **EmotionEngine V2**: Tracks energy (0.0–1.0) per turn with positive/negative keyword triggers, negation detection, overflow clamping (±0.06/turn), and mode labels ("Dead Battery" → "Hyper")
- **Circadian Rhythm**: Baseline energy varies by time of day (e.g. 0.22 at 2–5 AM, 0.80 at 11 PM–2 AM)
- **DriveMemory**: Google Drive-backed persistent storage with Vertex AI `text-multilingual-embedding-002` for semantic search; falls back to in-memory dict if Drive is unavailable
- **Camelot Wheel**: Harmonic mixing system for DJ set building (±1 key compatibility)
- **LUFS**: Loudness Units Full Scale — mastering target at -12 LUFS
- **LiveKit**: WebRTC framework used in V2 for browser-to-agent audio (retained in codebase for reference)

## Development Guidelines

### Running the V2.5 Agent
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-native.txt
cp .env.native.example .env
# Set GOOGLE_API_KEY in .env
.venv/bin/python claire.py
```

### Running the Frontend
```bash
npm install
npm run dev          # Dev server on :5173
npm run build        # Production build
```

### Running V2 via Docker
```bash
docker compose up --build
```

### Environment Variables
- `GOOGLE_API_KEY` — Gemini API key (required)
- `CLAIRE_MODEL` — Model ID (default: `gemini-2.5-flash-native-audio-preview`)
- `CLAIRE_VOICE` — Voice name: Aoede (warm), Kore (energetic), Puck (lively), Charon (deep), Fenrir (distinctive)
- `GOOGLE_CLOUD_PROJECT` — GCP project for Vertex AI embeddings
- `GOOGLE_CLOUD_LOCATION` — GCP region

### Conventions
- Frontend changes go in `src/` only
- Run `npm run build` after significant frontend changes
- Keep diffs small and focused
- Do not revive anything from `_archive/`
- Language: Code comments and persona content are in German
- The persona speaks German (Frankfurt dialect) — do not change her language or identity
- Never expose API keys or credentials in commits

### Branching
- `main` is the default branch
- Feature branches follow `claude/<description>`

## For AI Assistants

- The primary entry point is `claire.py` (V2.5 standalone agent)
- `agent.py` and `agent_telemetry.py` are the V2 LiveKit-based agents — kept for reference, not active development
- `persona.py` contains the full identity system — changes here affect Claire's personality, emotional dynamics, and speech patterns. Edit with care.
- `memory.py` handles persistent state — facts, ego energy, transcripts. Changes affect cross-session continuity.
- The frontend uses Vite (not Next.js), Zustand for state, and communicates via LiveKit/WebRTC + token endpoint
- Focus on emotional UX with clear states: idle, listening, speaking, error
- No image generation in this repo — that happens externally
- `node_modules/` is committed (visible in repo) — consider adding it to `.gitignore`

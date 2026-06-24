# Claire V2.5 — Native Audio

## Übersicht

Gemini Native Audio Voice Agent mit lokalem Browser-Dashboard. SQLite-primary Memory, WebGL Shader Engine, EmotionEngine.

## Architektur

- `launcher.py` → Entry Point (Preflight-Checks, Port 8550, uvicorn)
- `dashboard.py` → FastAPI (REST API + WebSocket Audio Bridge)
- `static/index.html` → Single-File Dashboard (WebGL, AudioWorklet, EmotionEngine)
- `claire.py` → Standalone CLI Agent (kein Dashboard)
- `memory.py` → SQLite-Primary unter `~/.claire_memory/claire.db`, Drive als async Backup
- `persona.py` → KKI Persona OS v1.0 (7 Layers) — **NICHT MODIFIZIEREN**

## Kritische Regeln

- **`persona.py` NICHT anfassen** — wird von `claire.py` und `dashboard.py` importiert
- **Original Claire V2 Repo** (`~/Documents/GitHub/claire-v2`) **NICHT anfassen**
- **GOOGLE_API_KEY** nur in `.env` (gitignored), NIE im Code oder Frontend
- **Port 8550** ist fest — kein Auto-Port-Hopping
- SDK Enum-Patch in `dashboard.py` Z.28-32 und `claire.py` Z.24-30 — nicht entfernen
- `send_tool_response(function_responses=responses)` — keyword arg Pflicht (SDK Bug)

## Start

```bash
.venv/bin/python launcher.py    # Dashboard + Browser
.venv/bin/python claire.py      # CLI-only
```

## API

| Endpoint | Methode | Beschreibung |
|----------|---------|-------------|
| `/api/health` | GET | Systemstatus (Gemini, LM Studio, SQLite, Drive) |
| `/api/memory` | GET | Facts gruppiert nach Kategorie |
| `/api/sessions` | GET | Session-History |
| `/api/config` | GET | Modell, Voice, Sample Rates |
| `/ws` | WS | Bidirektionale Audio-Bridge |

## Memory

SQLite-Primary (`~/.claire_memory/claire.db`) mit WAL-Mode. Tabellen: `facts`, `ego_state`, `summaries`, `transcripts`, `sessions`, `sync_queue`. Google Drive ist optionaler async Backup via `GDRIVE_MEMORY_FOLDER_ID`.

## Dependencies

`requirements-native.txt` — google-genai, pyaudio, python-dotenv, fastapi, uvicorn, google-auth, google-api-python-client, vertexai (optional).

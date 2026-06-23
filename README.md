<div align="center">

<img src="https://img.shields.io/badge/Claire-V2.5_Native_Audio-blueviolet?style=for-the-badge&logo=googlecloud&logoColor=white" alt="Claire V2.5"/>
<img src="https://img.shields.io/badge/Gemini-Native_Audio-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Gemini Native Audio"/>
<img src="https://img.shields.io/badge/Full_Duplex-200ms-00C853?style=for-the-badge" alt="Full Duplex"/>
<img src="https://img.shields.io/badge/EmotionEngine-v2-FF6D00?style=for-the-badge" alt="EmotionEngine"/>
<img src="https://img.shields.io/badge/Memory-Persistent-7C4DFF?style=for-the-badge" alt="Memory"/>

<br/><br/>

**Standalone upgrade von [Claire V2](https://github.com/KKEEY92/claire-v2).**<br/>
Gemini Native Audio ersetzt die komplette STT→LLM→TTS Pipeline.<br/>
Kein LiveKit, kein Web-Framework, kein Docker. Nur Mikrofon → Gemini → Lautsprecher.

</div>

---

## Was ist anders als V2?

| | Claire V2 | Claire V2.5 (Native Audio) |
|---|---|---|
| **Architektur** | Google STT → Gemini LLM → Google TTS (Chirp3-HD) | Gemini Native Audio (alles in einem) |
| **Latenz** | ~800ms (3 API-Calls) | ~200ms (1 Session) |
| **Duplex** | Half-Duplex (abwechselnd) | **Full-Duplex** (gleichzeitig hören + sprechen) |
| **Infrastruktur** | LiveKit + Cloud Run + Docker | **`python claire.py`** |
| **Stimme** | Google TTS Chirp3-HD | Gemini Neural Voices (Aoede, Kore, etc.) |
| **Prosodie** | TTS-Parameter (rate, gain) | Prompt-gesteuert (natürlicher) |
| **Dependencies** | ~15 Packages + LiveKit Server | 7 Packages, kein Server |

## Was gleich geblieben ist

- **KKI Persona OS v1.0** — 7-Layer Identity Framework (`persona.py`)
- **EmotionEngine v2** — Energie-Tracking über Turns, zirkadiane Rhythmen
- **Persistente Memory** — Google Drive + Vertex AI Embeddings (`memory.py`)
- **Tools** — `save_memory`, `recall_memory`

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

# 4. Starten
.venv/bin/python claire.py
```

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│  claire.py                                                  │
│                                                             │
│  ┌──────────┐    ┌────────────────────────────────────┐     │
│  │ Mikrofon │───▶│  Gemini 2.5 Flash Native Audio     │     │
│  │ (pyaudio)│◀───│  • Audio-in / Audio-out             │     │
│  └──────────┘    │  • Full-Duplex                      │     │
│       ▲          │  • Claires Persona (System Prompt)   │     │
│       │          │  • Tool Calling (Memory)             │     │
│  ┌────┴────┐     └──────────┬─────────────────────────┘     │
│  │ Speaker │                │                               │
│  │(pyaudio)│     ┌──────────▼─────────────────────────┐     │
│  └─────────┘     │  EmotionEngine + Memory             │     │
│                  │  • EgoState (Energie 0.0–1.0)       │     │
│                  │  • Prosodie via Prompt               │     │
│                  │  • Google Drive Persistence          │     │
│                  └────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Konfiguration (.env)

```env
# Gemini API Key (kostenlos: aistudio.google.com/apikey)
GOOGLE_API_KEY=...

# Modell
CLAIRE_MODEL=gemini-2.5-flash-native-audio-preview

# Stimme
#   Aoede    — weiblich, warm, empathisch (Default)
#   Kore     — weiblich, jung, energisch
#   Puck     — männlich, lebendig
#   Charon   — männlich, tief, ruhig
#   Fenrir   — männlich, markant
CLAIRE_VOICE=Aoede

# Google Cloud (für Memory-Embeddings)
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=europe-west3
```

## Dateien

| Datei | Beschreibung | Status |
|-------|-------------|--------|
| `claire.py` | Standalone Native Audio Agent | ✨ NEU |
| `requirements-native.txt` | Dependencies für claire.py | ✨ NEU |
| `.env.native.example` | Config-Template für claire.py | ✨ NEU |
| `agent.py` | Original V2 LiveKit Agent (Referenz) | unverändert |
| `persona.py` | KKI Persona OS v1.0 | unverändert |
| `memory.py` | DriveMemory + Embeddings | unverändert |

## Verwandte Repos

| Repo | Beschreibung |
|------|-------------|
| [claire-v2](https://github.com/KKEEY92/claire-v2) | Original mit LiveKit Pipeline (Production) |
| [Claire-V2-Architecture](https://github.com/KKEEY92/Claire-V2-Architecture) | Architektur-Dokumentation |
| [Aria](https://github.com/KKEEY92/Aria---Your-AI-Companion) | AI Companion mit Gemini Native Audio (React) |
| **claire-v2.5-native-audio** | ← dieses Repo |

## Lizenz

MIT

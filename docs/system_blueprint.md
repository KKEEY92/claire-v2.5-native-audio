# 🌌 System-Blueprint & KKI Master-Akte

Diese Datei dient als **Single-Source-of-Truth** (Backup-Protokoll und Master-Akte) für das `claire-v2.5-native-audio` System. 
Jeder KI-Agent, der in die Entwicklung oder Modifikation dieses Systems einsteigt, **MUSS** diese Datei lesen, um Kontext, Abhängigkeiten und Architektur-Richtlinien zu verstehen.

---

## 1. System Architektur (Monorepo)

Das System folgt einem strikten Monorepo-Ansatz, in dem native Edge-Clients (macOS/iOS) mit einem asynchronen Python-Core (Backend) gekoppelt werden.

### Komponenten:
- **Core AI Agent (`backend/claire.py`):** Behandelt Echtzeit-Audio und Video via LiveKit. Nutzt LLMs (GPT-4o) und High-Fidelity TTS (z.B. ElevenLabs, Cartesia) für lebensechte, akzentfreie, emotionale Konversationen (inkl. Lachen).
- **Control Dashboard (`backend/dashboard.py`):** FastAPI-App mit Websockets. Bietet UI für Persona-Management (Obsidian-Style), Context-Extraction und Agenten-Steuerung.
- **Masterakte (`data/personas/`):** JSON/Markdown basierter Langzeitspeicher. Das Dashboard extrahiert automatisch relevanten Kontext aus Rohtexten und verankert ihn hier.
- **Native Clients (`apps-workspace/`):** Entwickelt mit Swift 5 & SwiftUI in Xcode 27. Beinhaltet zwei Targets (`ClairemacOS` und `ClaireiOS`) innerhalb des `Claire.xcworkspace`.

---

## 2. Abhängigkeiten (Dependency Tree)

### 🐍 Python Backend
- `Python 3.12+`
- `fastapi`, `uvicorn` (Dashboard Server)
- `livekit-agents`, `livekit-api` (Echtzeit Audio/Video WebRTC)
- `openai` (Kognition, Context-Extraktion)
- `python-dotenv` (Umgebungsvariablen Management)
- `jinja2` (Templating für das Dashboard)
- `python-multipart` (File-Uploads und Export/Import)

### 🍏 Native Clients (Xcode)
- `Xcode 27.0 Beta` (oder neuer)
- `Swift 5.0+`
- `macOS 14.0+` Deployment Target (MenuBar App, Agentic Control)
- `iOS 16.0+` Deployment Target (Mobile Agent Access)
- *Geplant:* `LiveKit iOS SDK` via Swift Package Manager für direkte WebRTC Audio-Streams ohne WebView.

---

## 3. Verwendungsanweisungen für KI-Agenten

> [!IMPORTANT]
> **Für alle zukünftigen Agenten (Antigravity etc.):**

1. **State of the Art erzwingen:** Nutze nur modernste Architektur-Patterns. Keine veralteten Bibliotheken. Python Code muss strikt asynchron (`asyncio`) und stark typisiert (`Type Hinting`) sein.
2. **SwiftUI Best Practices:** Modifiziere die `ClairemacOS` App nur mit den neuesten SwiftUI Konzepten (z.B. `@Observable` statt `@StateObject`, wenn anwendbar).
3. **Pfade und Navigation:** Die Xcode-Projekte teilen sich den Code via dem `apps-workspace/Source` Verzeichnis. Achte darauf, relative Pfade im `.pbxproj` nicht zu zerstören (`path = Source;`).
4. **Context Extraktion:** Wenn du das Persona-System anpasst, aktualisiere die Logik in `backend/persona.py`. Die KI abstrahiert dort rohe Texte mithilfe von LLMs und fügt neues Wissen als "Erinnerungen" (Memories) an.
5. **TTS & Voice:** Für "lebensechte" Stimmen ist ElevenLabs oder Cartesia im LiveKit Agent zu konfigurieren. Achte darauf, die Latenz (VAD -> STT -> LLM -> TTS) unter 500ms zu halten!

---

## 4. Disaster Recovery & Setup

Wenn das System von Grund auf neu gestartet werden muss:

1. **Python Environment:** `pip install -r backend/requirements.txt`
2. **Xcode Derived Data Bug:** Falls Xcode beim Kompilieren mit `Code=28 "No space left on device"` abstürzt, leere `~/Library/Developer/Xcode/DerivedData/*` und baue mit `SWIFT_USE_EXPLICIT_MODULE_BUILD=NO`.
3. **Missing Configs:** Die LiveKit URL, Keys und OpenAI Keys müssen zwingend als Umgebungsvariablen (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `OPENAI_API_KEY`) vorhanden sein, da sonst der `claire.py` Agent crasht.

---
*Zuletzt aktualisiert: 14. Juli 2026. Autor: KKI & Antigravity.*

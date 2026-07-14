# 🌌 Claire V2.5 – Next-Gen Conversational AI Monorepo

Willkommen im hochmodernen **Claire V2.5** Repository. Dieses Monorepo vereint die mächtige, echtzeitfähige Python-Backend-Infrastruktur mit den nativen, extrem performanten Apple-Clients (macOS & iOS) in einer harmonischen, agentischen Architektur.

Dieses System wurde für **maximale Kognition, minimale Latenz und native Integration** entworfen.

---

## 🚀 Vision & Architektur

Claire ist nicht einfach nur ein Chatbot – sie ist eine vollständig integrierte **Conversational AI Person**. Sie nutzt eine Obsidian-ähnliche Masterakte als Langzeitgedächtnis, analysiert neuen Kontext automatisch und spricht auf Deutsch mit lebensechter Stimmmodulation (inklusive Emotionen und Lachen über LiveKit & ElevenLabs/Cartesia).

Das Projekt ist als **Monorepo** strukturiert, das Backend und Frontend sauber trennt, aber sofort einsatzbereit koppelt.

### 📁 Verzeichnisstruktur

```text
claire-v2.5-native-audio/
│
├── backend/                  # 🧠 Python KI-Backend & LiveKit WebRTC Server
│   ├── claire.py             # Haupt-Agent (Voice, Vision, Context)
│   ├── dashboard.py          # FastAPI & Socket.IO Dashboard-Server
│   ├── persona.py            # Obsidian-Style Persona Manager & Masterakte-Extraktor
│   └── static/               # Frontend Dashboard (HTML/JS/CSS)
│
├── apps-workspace/           # 🍏 Native Apple Clients (Xcode 27)
│   ├── Claire.xcworkspace    # Gemeinsamer Workspace für iOS & macOS
│   ├── ClairemacOS/          # Native macOS MenuBar App (SwiftUI)
│   └── ClaireiOS/            # Native iOS App (SwiftUI)
│
├── docs/                     # 📚 System-Blaupausen & Architektur-Dokumentation
│   └── system_blueprint.md   # WICHTIG: Die Master-Referenz für KI-Agenten
│
├── assets/                   # 🖼️ Icons, Logos, Persona-Bilder
├── data/                     # 💾 Lokale Speicher für Kontexte, Erinnerungen & Logs
└── scripts/                  # 🛠️ Nützliche Scripte (Start-Scripte, Utils)
```

---

## 🛠️ Tech Stack & Dependencies

- **Backend:** Python 3.12+, FastAPI, LiveKit Agents Framework, OpenAI (GPT-4o), ElevenLabs (TTS), asyncio.
- **Frontend (Dashboard):** HTML5, Vanilla JS, Tailwind CSS, Socket.IO.
- **Native Clients:** Swift 5+, SwiftUI, Xcode 27+, LiveKit Swift SDK (geplant).
- **Datenhaltung:** JSON/Markdown basierte lokale "Masterakte" (Obsidian-Style) für Personas und Erinnerungen.

---

## 🏁 Quick Start

### 1️⃣ Backend Starten

Das Backend erfordert LiveKit Keys und API Keys. Stelle sicher, dass du in deiner Umgebungsvariable oder `.env` Datei alle nötigen Keys gesetzt hast.

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt # (Stelle sicher, dass requirements installiert sind)

# Starte den KI-Agenten:
python3 claire.py start

# Starte in einem separaten Terminal das Control-Dashboard:
python3 dashboard.py
```

Das Dashboard erreichst du nun unter: `http://localhost:8000`

### 2️⃣ Native Apps Starten (macOS / iOS)

Öffne den Workspace in Xcode:

```bash
open apps-workspace/Claire.xcworkspace
```

1. Wähle das Target `ClairemacOS` oder `ClaireiOS`.
2. Klicke auf **Run** (⌘ + R).

---

## 🧠 Das Control Dashboard

Das Control Dashboard ist dein Command Center für Claire. Es bietet:
- **Obsidian Persona Archiv:** Lege Charakterzüge, Erinnerungen und Hintergrundgeschichten in einem strukturierten Markdown-Format an.
- **Context Extractor:** Füge Rohtexte ein. Das System extrahiert automatisch wichtiges Wissen und fügt es in die Masterakte der jeweiligen Persona ein.
- **Voice & TTS Controls:** Passe Claires Stimme (z.B. Emotion, Geschwindigkeit) in Echtzeit an.
- **Recording & Export:** Schneide Gespräche mit und exportiere Logs zur späteren Analyse.

---

## 📜 Agentic Blueprint

Dieses Repository wurde in Zusammenarbeit mit **Antigravity** (Agentic AI) erstellt.  
Wenn ein zukünftiger KI-Agent dieses System erweitern soll, weise ihn an, die Datei `docs/system_blueprint.md` zu lesen. Sie enthält alle Systemabhängigkeiten, Design-Philosophien und Protokolle.

*“Built with 🧠 and ⚡️ by KKI Systems & Antigravity”*

# Claire V2 — Zustandsbericht & Verbesserungsplan

**Projekt:** `00_CLAIRE_V2_APP`  
**Stand:** 2026-06-04  
**Autor:** Grok (Scan + Analyse)  
**Zielgruppe:** Kevin Kuck (Kev)

---

## 1. Executive Summary

Claire V2 ist ein **ambitioniertes, gut dokumentiertes Voice-AI-System** mit starkem Backend (LiveKit + Gemini + EmotionEngine + Drive-Memory) und einem **funktionsfähigen, aber noch dünnen Frontend**. Die Kern-Pipeline (Sprache rein/raus, Persona, Memory-Tools, Post-Call) ist implementiert. Die UI liefert bereits Verbindung, Telemetrie (Energie/Mood) und drei Views — viele Bereiche sind jedoch **visuell vorhanden, funktional noch Demo/Platzhalter**.

| Bereich | Reifegrad | Kurzfassung |
|--------|-----------|-------------|
| **Backend Agent** (`agent.py`) | 🟢 Hoch | Production-nah, RAM-optimiert (nur Google) |
| **Persona / Memory** | 🟢 Hoch | Deterministische Emotion + Drive RAG |
| **Token-Server** | 🟢 Fertig | Lokal + Vite-Proxy |
| **Frontend Call-UI** | 🟡 Mittel | LiveKit-Anbindung, Audio-Fix, wenig Fehler-UX |
| **AuraTone / Analytics** | 🔴 Niedrig | Größtenteils UI-Shell |
| **Repo-Hygiene** | 🟡 Mittel | Doppeltes Frontend, veraltete Docs |

**Build-Status Frontend:** `npm run build` ✅ erfolgreich (PWA ~658 KB precache, LiveKit-Bundle groß).

---

## 2. Projektstruktur (Ist)

```
00_CLAIRE_V2_APP/
├── agent.py              # LiveKit Voice-Agent (~440 Zeilen) — HAUPT-BACKEND
├── persona.py            # EmotionEngine, Circadian, EgoState
├── memory.py             # Drive Memory 2.0 (7 Kategorien, Fallback In-Memory)
├── brain_test.py         # Text-only Validierung (Vertex, ohne Audio)
├── token_server.py       # JWT für Frontend (Port 3001)
├── requirements.txt
├── package.json          # Vite + React 18 Frontend (Root!)
├── src/                  # ✅ Aktives Frontend (14 TS/TSX-Dateien)
├── claire-v2-frontend/   # ⚠️ Veraltetes Vite-Counter-Template — nicht nutzen
├── AGENTS.md             # ⚠️ Verweist noch auf claire-v2-frontend/
├── README.md             # Ausführlich, Phase 3–4 „in progress“
├── *.docx                # Architektur-Dossiers (Memory, EmotionEngine, Audio)
└── .agents/rules/        # 4-Phasen-Pipeline
```

**Wichtig:** Die **laufende App** liegt im **Projektroot** (`src/`), nicht unter `claire-v2-frontend/`.

---

## 3. Technischer Ist-Zustand

### 3.1 Backend (Python)

| Komponente | Status | Details |
|------------|--------|---------|
| LiveKit Agents 2.x | ✅ | `AgentSession` + `ClaireAgent` |
| STT / LLM / TTS | ✅ | Google `de-DE`, Gemini 2.5 Flash, Chirp3-HD TTS |
| EmotionEngine | ✅ | ±0.08 Clamp, Trigger-Wörter, Circadian-Blend 70/30 |
| Tools | ✅ | `save_memory`, `recall_memory`, `aura_master_track`, `create_camelot_playlist` |
| Telemetrie → UI | ✅ | Data Channel JSON `{ type: "telemetry", energy, moodTag }` |
| Post-Call | ✅ | Transcript, Ego persist, Gemini-Summary → Drive |
| Custom `tts_node` | ✅ | Buffer + StreamAdapter für Non-Streaming-TTS |
| VAD (Silero) | ❌ Entfernt | RAM-Fix — LiveKit Turn-Detection |

**Hinweis `requirements.txt`:** Enthält noch `livekit-agents[google,deepgram,elevenlabs,silero]` — widerspricht dem RAM-Fix in `agent.py`. Sollte auf `[google]` reduziert werden.

**Hinweis `agent_telemetry.py`:** Scheint Duplikat/Alter Stand von `agent.py` (gleicher Header) — konsolidieren oder löschen.

### 3.2 Frontend (React + Vite)

| Modul | Datei | Funktion | Reife |
|-------|-------|----------|-------|
| App-Shell | `App.tsx` | 3 Views, Token-Fetch, LiveKit enable | 🟡 |
| LiveKit Hook | `useLiveKit.ts` | Connect, Mic, Audio attach, Telemetry | 🟢 |
| Call | `PhoneCallScreen.tsx` | Status, NeonRing, FFT, Hang-up | 🟡 |
| Mood | `MoodGlow.tsx` | Energie-Farben aus Store | 🟢 |
| AuraTone | `AuraToneView`, `CamelotWheel` | Nur Visual + LiveStatus | 🔴 |
| Analytics | `AnalyticsView.tsx` | `factsCount` statisch, Session `--:--` | 🔴 |
| State | `emotionStore.ts` (Zustand) | energy, mood, connected, speaking | 🟢 |

**Umgebungsvariablen** (`.env.example`):

- `VITE_LIVEKIT_URL`
- `VITE_LIVEKIT_TOKEN_ENDPOINT` (oder Vite-Proxy `/token` → `:3001`)

### 3.3 Lokaler Start (referenz)

```bash
# Terminal 1 — Token
python token_server.py

# Terminal 2 — Agent (LiveKit Worker)
python agent.py start   # bzw. livekit-cli dev

# Terminal 3 — UI
npm run dev             # http://localhost:5173
```

---

## 4. Was gut funktioniert

1. **Architektur-Kohärenz:** README, Docx-Dossiers und Code (Persona/Memory/Tools) passen zusammen.
2. **EmotionEngine im Loop:** User-Turn → Energie-Shift → Telemetry → UI (`MoodGlow`, `NeonRing`).
3. **Audio-Ausgabe-Fix:** `TrackSubscribed` + DOM-`audio`-Element (häufige LiveKit-Falle gelöst).
4. **Memory-Pflicht im Prompt:** `save_memory` bei neuen Fakten — mit Post-Call-Summary.
5. **brain_test.py:** Schnelle Validierung ohne Audio-Kosten.
6. **PWA-Grundlage:** `vite-plugin-pwa` — installierbar auf iPhone/Mac.

---

## 5. Lücken & Risiken

### Kritisch (Funktionalität / Wartung)

| # | Problem | Auswirkung |
|---|---------|------------|
| K1 | **Zwei Frontends** (`src/` vs `claire-v2-frontend/`) | Verwirrung, falsche Agent-Anweisungen |
| K2 | **Keine echte Fehler-UX** bei Token/Agent/Mic | User sieht „Connecting…“ endlos |
| K3 | **`factsCount` wird nie befüllt** | Analytics-View zeigt immer 0 |
| K4 | **Hang-up trennt Room nicht explizit** | `onEndCall` setzt nur `active=false` — Zombie-Sessions möglich |
| K5 | **AuraTone-Tools sind Mock** | `aura_master_track` / `create_camelot_playlist` liefern Text, keine echte DSP/.nml |

### Mittel (UX & Produktwert)

| # | Problem | Auswirkung |
|---|---------|------------|
| M1 | **FFTAnalyzer = Synthetik** | Kein echtes Agent-Audio-Spektrum |
| M2 | **CamelotWheel = Deko** | Keine Key-Auswahl, kein Export, kein Traktor-Link |
| M3 | **Kein Transcript live** | Gespräch nur post-call in Drive — nicht in UI |
| M4 | **Kein Memory-Browser** | Kev kann gespeicherte Fakten nicht sehen/korrigieren |
| M5 | **AGENTS.md / README veraltet** | React-Version, Pfad, Phasen-Status |
| M6 | **Bundle >500 KB** | LiveKit-Client dominiert — kein Code-Splitting |

### Niedrig (Qualität)

| # | Problem |
|---|---------|
| N1 | Kein `npm run lint` / Tests |
| N2 | UI teils Englisch (`Listening...`, `Data Stream`) |
| N3 | `agent_telemetry.py` redundant |
| N4 | `.env` im Repo-Index (gitignored, aber lokal vorhanden — OK wenn nicht committed) |

---

## 6. Verbesserungsvorschläge (Funktionalität erhöhen)

Priorisiert nach **Impact × Aufwand**. Empfohlene Reihenfolge für die nächsten Sprints.

### Phase A — Quick Wins (1–2 Tage)

| Prio | Maßnahme | Nutzen |
|------|----------|--------|
| **A1** | **Repo aufräumen:** `claire-v2-frontend/` archivieren oder löschen; `AGENTS.md` auf Root-`src/` aktualisieren | Keine falschen Edits mehr |
| **A2** | **Verbindungs-State-Machine:** `idle → token → connecting → connected → error` mit `aria-live` + Retry-Button | Claire wirklich „benutzbar“ bei Fehlern |
| **A3** | **Sauberes Beenden:** `useLiveKit.disconnect()` + `room.disconnect()` bei Hang-up; optional Agent-Job beenden | Keine hängenden Sessions |
| **A4** | **Telemetry erweitern:** Agent sendet `factsCount`, `sessionSeconds`, `turnCount` | Analytics wird echt |
| **A5** | **`requirements.txt` straffen:** nur `[google]`; `flask`/`livekit-api` für Token-Server dokumentieren | Schnellere Installs, weniger RAM-Risiko |

### Phase B — Produkt-Features (3–7 Tage)

| Prio | Maßnahme | Nutzen |
|------|----------|--------|
| **B1** | **Live-Transcript-Panel** (Data Channel oder LiveKit Transcription Events) | Nachvollziehbarkeit, Debugging, Vertrauen |
| **B2** | **Memory-UI:** Liste der Drive-Facts (API-Endpoint `GET /memory` am Token-Server oder kleines Flask-Modul) | Kev sieht was Claire „weiß“ |
| **B3** | **Echter Audio-Visualizer:** `AnalyserNode` auf attached Agent-Audio-Element | FFT reagiert auf Claires Stimme |
| **B4** | **Camelot Wheel interaktiv:** 24 Keys klickbar → `create_camelot_playlist` mit echtem Key → Download `.m3u`/`.nml` Stub oder Pfad zu Traktor-Export-Skript | AuraTone wird Werkzeug, nicht Deko |
| **B5** | **Session-Timer + Post-Call-Summary in UI** nach Disconnect | Analytics vollständig |

### Phase C — Integration & Skalierung (1–2 Wochen)

| Prio | Maßnahme | Nutzen |
|------|----------|--------|
| **C1** | **AuraMaster echte Anbindung:** Tool ruft lokales Python/CLI auf (`subprocess` oder Cloud Function) statt Random-LUFS-Text | Audio-Partner-Credibility |
| **C2** | **Traktor-Bridge:** Export `collection.nml` Snippet oder Pfad zu `01_Master_Audio` (Kev-Setup) | Claire ↔ DJ-Workflow |
| **C3** | **Ein Start-Skript** `start_claire_local.sh` (Token + Agent + Vite) | Wie CV Manager Setup |
| **C4** | **Cloud Run + Frontend:** `VITE_*` auf deployed Token-Endpoint; Health-Dashboard | Mobile ohne localhost |
| **C5** | **Vitest + Playwright Smoke:** Token-Endpoint, Connect-Mock | Regression-Schutz |

---

## 7. Detail-Empfehlungen pro View

### 📞 Call

- Mikrofon-Permission vor Connect abfragen mit deutscher Erklärung.
- Anzeige: `Energie 72% · Spark · 14 Fakten` unter dem Namen.
- VAD-Indikator: „Du sprichst“ / „Claire spricht“ (aus `isSpeaking` + lokalem Mic-Level).

### 🎛️ AuraTone

- Seed-Key wählen (8A, 9B, …) → Playlist-Vorschau als Liste.
- Optional: BPM-Range, Energy-Filter aus EmotionEngine-Energy mappen (spielerisch).

### 📊 Analytics

- Echte Metriken: Gesprächsdauer, Turns, Facts neu in Session, letzte Summary (aus Drive oder API).
- Mini-Chart Energie-Verlauf pro Session (Array im Telemetry-Payload).

---

## 8. Abgleich README vs. Realität

| README behauptet | Code-Ist |
|------------------|----------|
| Phase 1–2 ✅ | Stimmt (`brain_test`, `agent.py`) |
| Phase 3 Frontend 🔄 | **Teilweise** — Call ok, Aura/Analytics shell |
| Phase 4 Deploy 🔄 | Cloud Run dokumentiert, nicht im Repo automatisiert |
| „Stitch + Vertex Design“ | Custom Vite/Tailwind UI |
| Projektstruktur nur Python-Files | **+ ganzes `src/` Frontend im Root** |

---

## 9. Sicherheit & Betrieb (Kurz)

- ✅ Secrets in `.env` / ADC — nicht im Frontend-Bundle (nur VITE_* URLs).
- ✅ Token-Server CORS nur localhost:5173.
- ⚠️ `gcloud run deploy --allow-unauthenticated` im README — Token-Endpoint absichern (API-Key oder IAP).
- ⚠️ Persönliche Transkripte in Drive — UI-Zugriff später mit Auth absichern.

---

## 10. Nächste konkrete Schritte (Empfehlung Kev)

1. **Entscheidung:** `claire-v2-frontend/` löschen/archivieren → eine Wahrheit: Root `src/`.
2. **A2 + A3 umsetzen** (Error-States + sauberes Disconnect) — größter UX-Gewinn für tägliche Nutzung.
3. **A4** — `factsCount` / `turnCount` in `_send_telemetry()` aus `_memory` + `_history`.
4. **B1 + B2** — Transcript + Memory-Liste (macht Claire „transparent“).
5. **Dann** Camelot/AuraMaster echt anbinden (B4/C1) — passt zu deinem DJ/Traktor-Ökosystem.

---

## 11. Anhang — Gescannte Kern-Dateien

| Datei | Zeilen (ca.) | Rolle |
|-------|--------------|-------|
| `agent.py` | 440 | Voice Pipeline + Tools + Post-Call |
| `memory.py` | 290 | Drive RAG |
| `persona.py` | 176 | Emotion + Tageskontext |
| `useLiveKit.ts` | 72 | WebRTC Client |
| `App.tsx` | 54 | Router Views |
| `brain_test.py` | 290 | Terminal-Test |

---

*Ende des Berichts. Bei Umsetzung einzelner Phasen (A1–C5) kann ein Follow-up „Implementierungs-CHANGELOG“ ergänzt werden.*
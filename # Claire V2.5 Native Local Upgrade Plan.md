# Claire V2.5 Native Local Upgrade Plan

## Summary

Claire V2.5 soll **Native-Audio-first** werden: Gemini Native Audio bleibt die Hauptpipeline, die bewährten Ideen aus Claire V2 werden übernommen, aber ohne LiveKit als Pflichtpfad. Ziel ist ein lokales Erlebnis, das sich wie eine echte Mac-App anfühlt: ein Start, kontrollierte Ports, klare Zustände, Live-Monitor, Memory-Transparenz und sauberes Audio-Lifecycle-Management.

Wichtiger Ist-Befund: `src/`, `agent.py`, `memory.py` und `vite.config.ts` sind zwischen `/Users/kevinkuck/Documents/GitHub/claire-v2` und `/Users/kevinkuck/claire-v2.5-native-audio` identisch. V2.5 unterscheidet sich vor allem durch `claire.py`, den untracked `dashboard.py` und `static/index.html`.

## Key Changes

- **Lokaler Launcher als Einstiegspunkt**
  - Neues `launcher.py` oder equivalent: startet `dashboard.py` kontrolliert auf `127.0.0.1:8550`.
  - Vor Start: Port `8550` prüfen, blockierenden Prozess mit PID anzeigen, kein Port-Hopping.
  - Desktop-Datei `Claire V2.5.command` soll nur noch diesen Launcher starten.
  - Keine automatische Nutzung von `3001`/LiveKit-Token-Server für den Native-Modus.

- **Native-Dashboard als Hauptprodukt**
  - `dashboard.py` wird offizieller lokaler Backend-Shell für V2.5.
  - `static/index.html` bleibt kurzfristig als schnelle UI bestehen, wird aber strukturiert an die V2-React-Ideen angeglichen: Call, Monitor, Memory, Analytics.
  - LiveKit-React-Code in `src/` bleibt Referenz/Archiv, wird nicht als Hauptpfad gestartet, solange Native Audio Ziel ist.

- **V2-Ideen sinnvoll portieren**
  - Aus V2 übernehmen: Connection-State-Machine, Live Monitor, Telemetrie, Sessiondauer, Turncount, FactsCount, Energy-Sparkline, Live-Transcript.
  - Nicht übernehmen: LiveKit Room, Token-Server als Pflicht, Cloud-Run-Token-Endpoint, alte Mehrprozess-Dev-Startlogik.
  - AuraTone bleibt vorerst UI/Tool-Idee, aber nicht erste Priorität.

- **Neue lokale Interfaces**
  - `GET /api/config`: Modell, Stimme, Sample-Rates, verfügbare Voices.
  - `GET /api/health`: Portstatus, Gemini-Key vorhanden, Memory/Drive verbunden, aktive Session, letzter Fehler.
  - `GET /api/memory`: lesbare Memory-Facts mit Kategorie und Inhalt.
  - `GET /api/sessions`: gespeicherte lokale Session-Metadaten.
  - `WS /ws`: bestehender Audio/Event-Kanal bleibt, erweitert um `status`, `transcript`, `emotion`, `memory`, `session`, `health`, `error`.

- **Stabilität**
  - Native-Audio-Session muss bei Disconnect Mic-Stream, Speaker-Context, WebSocket und Gemini-Session schließen.
  - Browser-Audio muss bei Stop Call alle Tracks stoppen und AudioContexts schließen.
  - Keine Secrets im Frontend; `GOOGLE_API_KEY` bleibt nur in Python/.env.
  - `.env.example` für V2.5 trennen oder deutlich markieren: Native-Modus nutzt `GOOGLE_API_KEY`, `CLAIRE_MODEL`, `CLAIRE_VOICE`; `VITE_*` nur für alte React/LiveKit-Schicht.

## Implementation Order

1. **Dirty-State sichern**
   - Vor Änderungen `git status` prüfen.
   - Bestehende untracked `dashboard.py` und `static/` als aktuelle Claude-Arbeit behandeln, nicht überschreiben.
   - `claire.py`-Diff mit Google-GenAI Enum-Patch beibehalten.

2. **Launcher & Portkontrolle**
   - Launcher implementieren.
   - `.command` auf Launcher umstellen.
   - Port `8550` strikt verwenden; bei Blockade klare Meldung mit PID und Kill-Hinweis.

3. **Health + Monitor**
   - `/api/health` ergänzen.
   - Dashboard rechts/oben um Health-Status erweitern: Gemini, Memory, WebSocket, Mic, Session, Port.
   - Browser darf nicht mehr auf `localhost:3001/token` als Native-Startziel zeigen.

4. **Memory + Session-Transparenz**
   - `/api/memory` und `/api/sessions` ergänzen.
   - Memory-Panel zeigt echte Facts statt nur Live-Events.
   - Nach Gespräch Session-Metadaten speichern: Dauer, Turns, Energie, Memory-Saves, Transkriptpfad.

5. **Audio UX**
   - Start/Stop robust machen.
   - Mic-Permission-Fehler sichtbar anzeigen.
   - Optional Geräteauswahl vorbereiten, aber nicht in v1 blockierend machen.
   - Latenz/Audio-Level nur anzeigen, wenn echte Messwerte vorhanden sind.

## Test Plan

- Start per `/Users/kevinkuck/Desktop/Claire V2.5.command` öffnet `http://localhost:8550`.
- Wenn `8550` belegt ist, startet kein zweiter Server und kein anderer Port wird genutzt.
- Start Call → WebSocket verbindet → `init/status/session` Events erscheinen.
- Stop Call → WebSocket geschlossen, Mic-Tracks gestoppt, keine hängenden AudioContexts.
- Memory-Save durch Toolcall erscheint im UI und bleibt nach Session abrufbar.
- `/api/health`, `/api/config`, `/api/memory`, `/api/sessions` liefern valide JSON-Antworten.
- `git status` nach Umsetzung zeigt nur beabsichtigte Dateien.
- Kein `npm run dev` oder Token-Server auf `3001` nötig für Native-V2.5.

## Assumptions

- Zielarchitektur: **Native only** als Hauptpfad; LiveKit bleibt Referenz/Fallback, nicht täglicher Start.
- Erster Meilenstein: **lokale App-Schale + kontrollierter Start**.
- Bestehende Claude-Code-Arbeit in `dashboard.py`, `static/` und `claire.py` wird erhalten und ausgebaut.
- GitHub-Connector hatte keinen Zugriff auf `KKEEY92/claire-v2`; der Vergleich basiert deshalb auf der lokalen Kopie unter `/Users/kevinkuck/Documents/GitHub/claire-v2`.

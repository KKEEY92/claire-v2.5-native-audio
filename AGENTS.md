# Claire V2 — Projekt (00_CLAIRE_V2_APP)

## Produkt
Claire V2: authentische KI für **emotionale Audio-Interaktion** (Memory-System 2.0, EmotionEngine). Architektur-Docs liegen als `.docx` im Projektroot — bei Architektur-Fragen darauf verweisen, nicht erfinden.

## Repo-Layout
- **`src/`** (Projektroot) — aktives Frontend (Vite, React, TypeScript) — **hier coden**
- **`package.json`**, **`vite.config.ts`**, **`index.html`** — Frontend-Tooling im Root
- **Python-Backend:** `agent.py`, `persona.py`, `memory.py`, `token_server.py`, `brain_test.py`
- **`_archive/`** — abgelegte, nicht aktive Artefakte (z. B. altes Vite-Template)
- Root: Konzept-/Architektur-Dokumente (`.docx`, `README.md`, `ZUSTANDSBERICHT_*.md`)

## Stack (Ist-Zustand)
- **Kein Next.js** — Vite SPA im Projektroot. Nicht auf App Router migrieren, außer Kevin fordert es explizit.
- Backend/GCP/Vertex: separat; Frontend spricht per LiveKit/WebRTC und Token-Endpoint (`token_server.py` / Vite-Proxy `/token`).

## Ziele beim Code-Heben
- Emotionale UX: Zustände klar (idle, listening, speaking, error); Feedback ohne UI-Overload.
- Audio-Pfade: Permissions, Fehlerzustände, Loading — von Anfang an robust.
- Performance: kleine Bundles, lazy Routes/Features wenn App wächst.
- a11y: Fokus, `aria-live` für Status, sinnvolle `alt`-Texte (aktuell teils leer — fixen).

## Arbeiten
- Frontend-Änderungen nur unter **`src/`** im Projektroot (nicht unter `_archive/`).
- `npm run build` nach größeren Frontend-Änderungen (`package.json` im Root).
- Kleine Diffs; keine Wiederbelebung des archivierten Vite-Counter-Templates.

## Abgrenzung (wichtig)
- **Kein** Bezug zu Bildgenerierung, Shoots oder Referenz-Avataren.
- Bild-Erstellung nur unter **`/Users/kevinkuck/Desktop/Grok/`** — dieses Repo nicht anfassen, keine `public/reference-models/`, nicht in die UI einbauen, außer Kevin fordert es explizit.

## Kevin
Deutsch, duzen, lebensecht. Globale Rules: `~/.grok/AGENTS.md`. Hyperfokus/Vibe/Architektur-Modi gelten.
# Claire V2 — Projekt (00_CLAIRE_V2_APP)

## Produkt
Claire V2: authentische KI für **emotionale Audio-Interaktion** (Memory-System 2.0, EmotionEngine). Architektur-Docs liegen als `.docx` im Projektroot — bei Architektur-Fragen darauf verweisen, nicht erfinden.

## Repo-Layout
- **`claire-v2-frontend/`** — UI (Vite 8, React 19, TypeScript 6) — **hier coden**
- Root: Konzept-/Architektur-Dokumente (kein App-Code)

## Stack (Ist-Zustand)
- **Kein Next.js** — Vite SPA. Nicht auf App Router migrieren, außer Kevin fordert es explizit.
- Backend/GCP/Vertex: separat; Frontend spricht später per API/WebSocket — Verträge typisieren (Zod/OpenAPI wenn vorhanden).

## Ziele beim Code-Heben
- Emotionale UX: Zustände klar (idle, listening, speaking, error); Feedback ohne UI-Overload.
- Audio-Pfade: Permissions, Fehlerzustände, Loading — von Anfang an robust.
- Performance: kleine Bundles, lazy Routes/Features wenn App wächst.
- a11y: Fokus, `aria-live` für Status, sinnvolle `alt`-Texte (aktuell teils leer — fixen).

## Arbeiten
- Frontend-Änderungen nur unter `claire-v2-frontend/src/`.
- `npm run lint` und `npm run build` nach größeren Änderungen.
- Kleine Diffs; Vite-Template-Reste (Counter-Demo) entfernen, wenn Claire-UI gebaut wird.

## Abgrenzung (wichtig)
- **Kein** Bezug zu Bildgenerierung, Shoots oder Referenz-Avataren.
- Bild-Erstellung nur unter **`/Users/kevinkuck/Desktop/Grok/`** — dieses Repo nicht anfassen, keine `public/reference-models/`, nicht in die UI einbauen, außer Kevin fordert es explizit.

## Kevin
Deutsch, duzen, lebensecht. Globale Rules: `~/.grok/AGENTS.md`. Hyperfokus/Vibe/Architektur-Modi gelten.
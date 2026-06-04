# Claire V2 Frontend — Vite + React 19

## Stack
- **Vite 8** (`vite.config.ts`), **React 19**, **TypeScript 6**
- ESLint flat config (`eslint.config.js`)
- Styles: `src/index.css`, `src/App.css` (noch Template — Richtung Design-Tokens ausbauen)
- Entry: `src/main.tsx` → `src/App.tsx`

## Dateien heben (.tsx .ts .css .json)
1. Lesen → Kurz-Score (Types, Struktur, Perf, a11y, Wartbarkeit).
2. Top-Fixes nach Impact; **kein** Full-Rewrite des Templates ohne Auftrag.
3. Diffs klein; `npm run lint` + `npm run build` verifizieren.

## React / TS
- Funktionale Components, Hooks; strikte Types (`strict` in tsconfig beachten).
- Komponenten aufteilen sobald `App.tsx` wächst: `components/`, `hooks/`, `lib/`, `types/`.
- State: lokal vs Context — erst Context wenn ≥2 Ebenen es brauchen.
- Externe Links: `rel="noopener noreferrer"` bei `target="_blank"`.
- Leere `alt=""` nur bei dekorativen Bildern; sonst beschreibend.

## CSS
- CSS-Variablen für Claire-Brand (Farben, Radius, Motion) in `:root`.
- Mobile-first; keine duplizierten Magic Numbers.
- Animation respektiert `prefers-reduced-motion`.

## JSON / Config
- `package.json`, `tsconfig*.json`: minimale Änderungen; keine Major-Upgrades ohne Hinweis.
- ESLint: type-aware Rules laut README aktivieren, wenn Codebase reif genug.

## Claire-spezifisch (UI-Richtung)
- Demo-Counter/ Vite-Marketing-Sections entfernen, wenn echte Claire-Shell gebaut wird.
- UI-States für Audio/EmotionEngine vorbereiten (auch wenn Backend noch mock).
- Keine Secrets im Frontend; Env nur `VITE_*` über `.env` (nicht committen).

## Commands
```bash
npm run dev      # lokal
npm run lint
npm run build
```

## Nicht tun
- **Keine** Shoot-Bilder, `reference-models/`, oder Prompt-Docs aus Bild-Sessions — Claire ist Audio/UI, keine Foto-Pipeline.
- Next.js/App Router einführen ohne expliziten Auftrag.
- Schwere UI-Libs ohne Abstimmung.
- `any`, ungenutzte Imports, tote Template-Assets behalten.
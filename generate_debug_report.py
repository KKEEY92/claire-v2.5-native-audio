#!/usr/bin/env python3
"""
Erzeugt den KKI-Debugging-/Implementierungs-Report (PDF) für Claire V2.

Legt das PDF ab:
  1. auf dem Desktop  (~/Desktop/CLAIRE_V2_Report_<DATUM>.pdf)
  2. im Projektordner (KKI_DEBUGGING-REPORT_CLAIRE-V2_<DATUM>.pdf)
"""
from datetime import date
from pathlib import Path
import shutil

from fpdf import FPDF

DATUM = date.today().isoformat()  # YYYY-MM-DD (KKI-Datumsformat)
PROJECT_DIR = Path(__file__).resolve().parent
DESKTOP = Path.home() / "Desktop"
DESKTOP_PDF = DESKTOP / f"CLAIRE_V2_Report_{DATUM}.pdf"
PROJECT_PDF = PROJECT_DIR / f"KKI_DEBUGGING-REPORT_CLAIRE-V2_{DATUM}.pdf"
FONT = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


class Report(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("B", "", FONT)
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(20, 20, 20)

    def h1(self, t):
        self.set_font("B", size=16); self.set_text_color(20, 40, 90)
        self.ln(3); self.multi_cell(self.epw, 9, t); self.set_text_color(0, 0, 0); self.ln(1)

    def h2(self, t):
        self.set_font("B", size=12); self.set_text_color(40, 70, 130)
        self.ln(2); self.multi_cell(self.epw, 7, t); self.set_text_color(0, 0, 0); self.ln(1)

    def p(self, t, size=10.5):
        self.set_font("B", size=size); self.multi_cell(self.epw, 5.4, t); self.ln(1.5)

    def b(self, t):
        self.set_font("B", size=10); self.multi_cell(self.epw, 5, f"  •  {t}")

    def code(self, t):
        self.set_font("B", size=9); self.set_text_color(70, 70, 70)
        self.multi_cell(self.epw, 4.6, t); self.set_text_color(0, 0, 0); self.ln(1)


def build():
    pdf = Report()
    pdf.add_page()

    # ── Cover ────────────────────────────────────────────────────────────────
    pdf.set_font("B", size=24); pdf.multi_cell(pdf.epw, 12, "CLAIRE V2")
    pdf.set_font("B", size=14); pdf.set_text_color(40, 70, 130)
    pdf.multi_cell(pdf.epw, 8, "Debugging- & Implementierungs-Report")
    pdf.set_text_color(90, 90, 90); pdf.set_font("B", size=10.5)
    pdf.ln(2)
    pdf.multi_cell(pdf.epw, 5.5,
        f"Projekt:      00_CLAIRE_V2_APP\n"
        f"Stand:        {DATUM} (KKI-Format)\n"
        f"Branch:       claude/goofy-jang-54e8eb  ·  PR #1\n"
        f"Erstellt:     Claude Code (Opus 4.8)\n"
        f"Umgebung:     macOS 27.0 Beta · Python 3.15.0a1 (Host) / Python 3.12 (Container)")
    pdf.set_text_color(0, 0, 0); pdf.ln(4)

    # ── 1. Executive Summary ─────────────────────────────────────────────────
    pdf.h1("1. Executive Summary")
    pdf.p("In dieser Session wurde Claire V2 substanziell erweitert und ein hartnäckiger "
          "Voice-Loop-Fehler forensisch bis auf die Betriebssystem-/Python-Ebene zurückverfolgt. "
          "Kernergebnisse:")
    pdf.b("Lokales LLM anschließbar (.env-Switch Google Gemini ⇄ LM Studio).")
    pdf.b("Stimme, Gedächtnis und Realismus deutlich verbessert (Streaming-TTS, Prosodie, "
          "proaktives RAG, Post-Call-Extraktion, konsistenter Tageskontext).")
    pdf.b("Root Cause des Greeting-Hangs gefunden: kaputter multiprocessing-IPC des "
          "LiveKit-PROCESS-Executors unter Python 3.15.0a1 (Job nach 60s als 'unresponsive' gekillt).")
    pdf.b("Containerisierung (Linux/Python 3.12) → stabiler PROCESS-Executor + Silero VAD; "
          "headless verifiziert: Claire empfängt Audio, transkribiert, antwortet, sendet Audio.")
    pdf.b("Verbleibendes Problem isoliert: Browser-WebRTC-Audio-Medium auf macOS 27 Beta "
          "(Datenkanal/Text funktioniert, RTP-Audio in beide Richtungen nicht).")
    pdf.b("Neuer Live-Monitor (LIVE-Tab) zeigt Metadaten + Claire-Livefeed/Terminal-Log — "
          "läuft über den Datenkanal, also auch trotz des Audio-Problems sichtbar.")

    # ── 2. Git-Commits ───────────────────────────────────────────────────────
    pdf.h1("2. Git-Commits dieser Session")
    commits = [
        ("ebe682d", "fix: on_enter Worker-Heartbeat-Timeout (process unresponsive @ 60s)"),
        ("9c2e37d", "feat: llm_node override — Layer-3 Feedback-Loop pro Turn"),
        ("43d7f78", "feat: .env LLM-Switch (Google ⇄ LM Studio) + <think>-Stream-Filter"),
        ("b27f388", "feat(realism): konsistenter Tag, rotierende Gedanken, Zeitgefühl"),
        ("e1f5403", "feat(memory): Facts-Cache, Thread-Offload, proaktives RAG + Post-Call-Extraktion"),
        ("3e34899", "feat(voice): energiegekoppelte Prosodie + echtes TTS-Streaming"),
        ("901c7cb", "docs: README-Changelog (Voice/RAG/Kontinuität)"),
        ("6967b1d", "fix(voice): env-gesteuerter Job-Executor (THREAD-Workaround) + Frontend-Audio-Guard"),
        ("26be037", "feat(docker): Agent + Token-Server containerisieren (Linux/Py3.12 + Silero VAD)"),
        ("a9aa4c6", "fix(frontend): TURN-Relay erzwingen + Remote-Audio via createMediaStreamSource"),
        ("eeb0e14", "fix(frontend): erzwungenes TURN-Relay zurücknehmen (Standard-ICE)"),
        ("50fc92e", "feat(monitor): Live-Monitor — Metadaten + Claire-Livefeed (Datenkanal & stdout)"),
    ]
    pdf.set_font("B", size=9)
    for h, m in commits:
        pdf.multi_cell(pdf.epw, 4.8, f"  {h}   {m}")
    pdf.ln(2)

    # ── 3. Implementierungen & Fixes ─────────────────────────────────────────
    pdf.add_page()
    pdf.h1("3. Implementierungen & Fixes im Detail")

    pdf.h2("3.1 Lokales LLM — .env-Switch (Google ⇄ LM Studio)")
    pdf.b("setup_llm() in agent.py: LLM_PROVIDER=google|lmstudio; OpenAI-kompatibler LM-Studio-Endpoint.")
    pdf.b("KEIN fnc_ctx (in livekit-agents 1.x nicht vorhanden) — Tools hängen an der Agent-Klasse.")
    pdf.b("openai-Plugin-Import am Modul-Top (Plugin-Registrierung muss im Main-Thread passieren).")
    pdf.b("Empfehlung verifiziert: Instruct-Modell (qwen2.5-7b-instruct) statt R1-Reasoning-Distill.")

    pdf.h2("3.2 <think>-Stream-Filter")
    pdf.b("ThinkTagFilter entfernt <think>…</think> deterministisch aus dem llm_node-Stream "
          "(robust über Chunk-Grenzen). Tool-Call-Chunks bleiben unangetastet.")
    pdf.b("Live-Befund: LM Studio liefert R1-Reasoning separat (reasoning_content); der Plugin "
          "liest nur content → kein Leakage. Filter bleibt als Netz für andere Backends.")

    pdf.h2("3.3 Realismus")
    pdf.b("Tagesstabiler RNG (random.Random(Datum)) → konsistenter Tagesinhalt über mehrere Anrufe.")
    pdf.b("Layer-3: 3 wiederkehrende Gedanken aus 9er-Pool, tagesstabil rotiert.")
    pdf.b("format_time_since() → Wiedersehens-Anker in Layer 5 ('Ihr habt gestern zuletzt geredet').")

    pdf.h2("3.4 Gedächtnis")
    pdf.b("In-Memory Facts-Cache; Drive-I/O + Vertex-Embeddings via asyncio.to_thread (Event-Loop frei).")
    pdf.b("Proaktives RAG im llm_node: relevante Fakten werden automatisch injiziert — unabhängig "
          "vom Tool-Calling (entscheidend für lokale Modelle).")
    pdf.b("Post-Call-Fakten-Extraktion als Sicherheitsnetz: Fakten persistieren auch ohne save_memory-Call.")

    pdf.h2("3.5 Stimme")
    pdf.b("tts_node: echtes Streaming (Text rein / Frames raus nebenläufig) statt Voll-Puffern → TTFT-Gewinn.")
    pdf.b("Energiegekoppelte Prosodie: speaking_rate + volume_gain_db pro Turn aus ego.energy.")

    pdf.h2("3.6 Root Cause: Greeting-Hang (macOS 27 Beta + Python 3.15.0a1)")
    pdf.p("Symptom: Greeting hing 60s, dann 'process is unresponsive, killing process'; keine TTS-Frames.")
    pdf.b("Ausgeschlossen (gemessen): LLM (7s isoliert), Embeddings, turn_detection-Parameter, "
          "Zombie-Prozesse, Cloud-Räume.")
    pdf.b("Ursache: multiprocessing-IPC-Healthcheck des PROCESS-Executors ist auf Python 3.15.0a1 defekt "
          "→ Job-Kindprozess wird fälschlich als 'unresponsive' gekillt.")
    pdf.b("Fix: env-gesteuerter Executor. LIVEKIT_JOB_EXECUTOR=thread (Mac) umgeht multiprocessing; "
          "im Linux-Container PROCESS (stabil). Zusätzlich onnxruntime fehlt auf 3.15a1 → kein Silero VAD lokal.")

    pdf.h2("3.7 Containerisierung (Linux / Python 3.12 + Silero VAD)")
    pdf.b("Dockerfile (python:3.12-slim) + docker-compose.yml: Services 'agent' + 'token-server'.")
    pdf.b("LM Studio bleibt auf dem Mac (GPU) → Agent erreicht es via host.docker.internal:1234.")
    pdf.b("Google ADC read-only gemountet (GOOGLE_APPLICATION_CREDENTIALS=/creds/adc.json).")
    pdf.b("Headless verifiziert: PROCESS-Executor stabil (kein 60s-Kill), Silero VAD aktiv, "
          "Claire empfängt Audio → transkribiert → antwortet (3 TTS-Antworten auf Test-Audio).")

    pdf.h2("3.8 Frontend-Audio-Fixes")
    pdf.b("createMediaStreamSource statt createMediaElementSource (letzteres ist für Remote-WebRTC "
          "in Chrome kaputt → kein Ton + flache Waveform). <audio>-Element spielt nativ ab.")
    pdf.b("iceTransportPolicy-Experiment: 'relay' stabilisierte die Verbindung (20s → Minuten), brachte "
          "das Audio-Medium aber nicht durch → zurück auf Standard-ICE.")

    pdf.h2("3.9 Live-Monitor (LIVE-Tab)")
    pdf.b("Agent sendet strukturierte Events + angereicherte Telemetrie (llmProvider, vadActive) über "
          "den LiveKit-Datenkanal: Greeting, Transkript, Tool-Calls, Energie-Shifts, RAG-Recall, Fehler.")
    pdf.b("log_server.py (Host, SSE /logs): streamt 'docker compose logs -f agent' live in den Browser.")
    pdf.b("LiveMonitorView: Metadaten-Header (Energie-Gauge+Sparkline, LLM/VAD-Badges), Live-Transkript, "
          "Terminal-Panel mit Umschalter EVENTS ⇄ RAW STDOUT.")

    # ── 4. Verbleibendes Problem ─────────────────────────────────────────────
    pdf.add_page()
    pdf.h1("4. Verbleibendes Problem — Browser-Audio auf macOS 27 Beta")
    pdf.p("Forensisch eingegrenzt: Auf dem Mac-Browser fließt das WebRTC-Audio-Medium (RTP) in keine "
          "Richtung; Signalisierung + Datenkanal (Text/Telemetrie) funktionieren. Beweise:")
    pdf.b("Claires Text erscheint (Datenkanal), ihre Stimme ist nicht hörbar (Audio-Medium).")
    pdf.b("Der Agent erhält kein User-Audio (kein STT-Transkript; STT-Audio-Timeout im Feed).")
    pdf.b("Headless-Client (anderer WebRTC-Stack) durchläuft die volle Schleife inkl. Audio fehlerfrei.")
    pdf.p("Schlussfolgerung: OS-Level-Defekt der Beta, vom App-Code nicht behebbar. Nächster Test: "
          "anderer Browser (Safari/Firefox auf localhost) bzw. anderes Gerät via HTTPS-Tunnel.")

    # ── 5. Architektur & Betrieb (README-Essenz) ─────────────────────────────
    pdf.h1("5. Architektur & Betrieb (Stand README)")
    pdf.h2("Stack")
    pdf.b("Voice: LiveKit Agents 1.1.7 (AgentSession + Agent).")
    pdf.b("STT/TTS: Google Cloud (de-DE, Chirp3-HD) — immer Cloud.")
    pdf.b("LLM: Gemini 2.5 Flash (Cloud) ⇄ qwen2.5-7b-instruct (lokal, LM Studio) via LLM_PROVIDER.")
    pdf.b("Memory: Google Drive (ADC) + Vertex-Embeddings; 7 Kategorien, Duplikatschutz >60%.")
    pdf.b("VAD: Silero (nur Container/Linux); auf dem Mac STT-Endpointing.")
    pdf.h2("Lokaler Start (Mac, THREAD-Executor)")
    pdf.code(".env: LLM_PROVIDER=lmstudio · LMSTUDIO_MODEL=qwen2.5-7b-instruct · LIVEKIT_JOB_EXECUTOR=thread\n"
             "LM Studio: lms load qwen2.5-7b-instruct -y --gpu max --context-length 8192\n"
             ".venv/bin/python token_server.py        # :3001\n"
             ".venv/bin/python agent.py dev           # Worker\n"
             "npm run dev                              # http://localhost:5173")
    pdf.h2("Container-Start (Linux/Python 3.12, PROCESS-Executor + Silero VAD)")
    pdf.code("docker compose up --build                # agent + token-server\n"
             "PATH=/opt/homebrew/bin:$PATH .venv/bin/python log_server.py   # :3002 (Live-Log)\n"
             "npm run dev -- --host                    # Frontend, Tab LIVE")

    # ── 6. Verifikation ──────────────────────────────────────────────────────
    pdf.h1("6. Verifikation (durchgeführt)")
    pdf.b("ThinkTagFilter: 6/6 Unit-Tests inkl. split-Tags.")
    pdf.b("Realismus/Memory/Prosodie: Logik-Unit-Tests grün; Drift-Varianz erhalten (kein Seed-Leak).")
    pdf.b("LM Studio: TTFT R1-14B = 17,2s (unbrauchbar) vs Qwen2.5-7B = 1,2s; Kontext-Fix 128K→8K: 18,4s→0,19s.")
    pdf.b("Container headless: Greeting-Audio (TTS-Frames), Silero VAD aktiv, kein 60s-Kill, "
          "Tool-Calling + Transkription auf publiziertes Test-Audio.")
    pdf.b("Live-Monitor: Telemetrie (llm=lmstudio, vad=True) + Events über Datenkanal; /logs streamt docker-Log.")

    # ── 7. Offene Punkte ─────────────────────────────────────────────────────
    pdf.h1("7. Offene Punkte / Empfehlungen")
    pdf.b("Browser-Audio macOS 27 Beta: anderes Gerät/Browser nutzen, bis Beta stabil (OS-Problem).")
    pdf.b("Live-Transkript ist best-effort über conversation-items (kann bei reinem Greeting timing-bedingt fehlen).")
    pdf.b("ADC ist User-Refresh-Token; für echtes Cloud-Deploy auf Service-Account-JSON umstellen.")
    pdf.b("Nicht Teil dieser Session (geplant, separat): Multi-User-Memory (user_id-Routing, "
          "/{user_id}/-Ordner, Firestore, persona_config.json).")
    pdf.b("agent_telemetry.py ist eine veraltete Kopie — Konsolidierung offen.")

    pdf.ln(4)
    pdf.set_font("B", size=8.5); pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(pdf.epw, 4.4,
        f"Erzeugt mit generate_debug_report.py · {DATUM} · "
        f"Ablage: Desktop + Projektordner (KKI-Format).")

    DESKTOP.mkdir(exist_ok=True)
    pdf.output(str(DESKTOP_PDF))
    shutil.copyfile(DESKTOP_PDF, PROJECT_PDF)
    print(f"✅ Desktop: {DESKTOP_PDF}  ({DESKTOP_PDF.stat().st_size} bytes)")
    print(f"✅ Projekt: {PROJECT_PDF}")


if __name__ == "__main__":
    build()

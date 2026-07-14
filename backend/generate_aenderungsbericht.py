#!/usr/bin/env python3
"""Generate PDF change report for Claire V2 session work."""

from datetime import date
from pathlib import Path

from fpdf import FPDF

PROJECT_DIR = Path(__file__).resolve().parent
OUTPUT = PROJECT_DIR / "CLAIRE_V2_Aenderungsbericht.pdf"
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"


class ReportPDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Body", "", FONT_PATH)
        self.set_auto_page_break(auto=True, margin=18)

    def section_title(self, title: str) -> None:
        self.set_font("Body", size=14)
        self.set_text_color(30, 64, 120)
        self.ln(4)
        self.multi_cell(self.epw, 9, title)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def body(self, text: str, size: int = 11) -> None:
        self.set_font("Body", size=size)
        self.multi_cell(self.epw, 6, text)
        self.ln(2)

    def bullet(self, text: str) -> None:
        self.set_font("Body", size=10)
        self.multi_cell(self.epw, 5, f"  -  {text}")


def build_pdf() -> None:
    pdf = ReportPDF()
    pdf.set_margins(20, 20, 20)
    pdf.add_page()

    pdf.set_font("Body", size=20)
    pdf.multi_cell(pdf.epw, 12, "Claire V2 — Änderungsbericht")
    pdf.set_font("Body", size=11)
    pdf.set_text_color(80, 80, 80)
    pdf.multi_cell(
        pdf.epw,
        6,
        f"Projekt: 00_CLAIRE_V2_APP\n"
        f"Stand: {date.today().isoformat()}\n"
        f"Erstellt von: Grok (Cursor Agent)\n"
        f"Git-Basis: Commits seit Initial Release (7a67e49)",
    )
    pdf.set_text_color(0, 0, 0)
    pdf.ln(6)

    pdf.section_title("1. Executive Summary")
    pdf.body(
        "In dieser Session wurde Claire V2 in mehreren inkrementellen Schritten verbessert: "
        "Repository aufgeräumt, LiveKit-Verbindung mit Zustandsmaschine und deutscher UI stabilisiert, "
        "Hang-up trennt die Room-Session sauber, Telemetrie liefert echte Analytics-Daten, und "
        "requirements.txt wurde an die RAM-optimierte Google-only-Pipeline angepasst."
    )

    pdf.section_title("2. Git-Commits (Übersicht)")
    commits = [
        ("a9fa755", "docs: Legacy-Frontend nach _archive/, AGENTS.md + README auf src/"),
        ("61639b8", "pre-task snapshot: Connection State Machine"),
        ("83abbee", "feat: LiveKit Connection State Machine + deutsche UI + Retry"),
        ("187c678", "fix: disconnect() bei Hang-up, vollständiger Store-Reset"),
        ("cc70ecd", "feat: Telemetrie factsCount, turnCount, sessionSeconds"),
        ("ff5e438", "chore: livekit-agents nur noch [google] in requirements.txt"),
    ]
    pdf.set_font("Body", size=10)
    for h, msg in commits:
        pdf.multi_cell(pdf.epw, 5, f"  {h}  -  {msg}")
    pdf.ln(4)

    pdf.section_title("3. Repo-Struktur & Dokumentation")
    pdf.bullet("Veraltetes Frontend claire-v2-frontend/ nach _archive/claire-v2-frontend/ verschoben.")
    pdf.bullet("AGENTS.md und README.md verweisen auf das aktive Frontend unter src/.")
    pdf.bullet("ZUSTANDSBERICHT_2026-06-04.md: Scan, Reifegrad-Matrix, Prioritäten A/B/C.")
    pdf.bullet(".env.example, .agents/rules, Workflows und Antigravity-Config ergänzt.")

    pdf.section_title("4. Connection State Machine (Frontend)")
    pdf.body("Ziel: Kein endloses „Connecting…“ bei Fehlern; klare deutsche Statusanzeige; Retry.")
    pdf.bullet("emotionStore.ts: connectionState (idle | token_fetch | connecting | connected | error), connectNonce, requestConnection / retryConnection / resetConnection.")
    pdf.bullet("useLiveKit.ts: Token-Fetch und room.connect() im Hook; State-Updates an jedem Schritt; Fehler → error.")
    pdf.bullet("PhoneCallScreen.tsx: Labels Verbinde… / Starte… / Verbunden / Fehler; aria-live=\"polite\"; Button „Erneut verbinden“.")
    pdf.bullet("App.tsx: sessionActive + requestConnection beim Start; Token-Logik aus App in den Hook verlagert.")

    pdf.section_title("5. Hang-up & LiveKit-Disconnect")
    pdf.body("Ziel: Keine Zombie-Sessions nach Auflegen; sauberer Neustart.")
    pdf.bullet("export function disconnect() in useLiveKit.ts: room.disconnect(true), Mikrofon aus, lokale Tracks stoppen, DOM-Audio entfernen.")
    pdf.bullet("Store-Reset: connectionState idle, isConnected/isSpeaking false, energy 0.65, moodTag null, Analytics-Felder 0.")
    pdf.bullet("PhoneCallScreen: Hang-up ruft disconnect() und onEndCall() (sessionActive=false).")
    pdf.bullet("connectGeneration verhindert, dass in-flight Connects nach Hang-up weiterlaufen.")

    pdf.add_page()
    pdf.section_title("6. Telemetrie & Analytics")
    pdf.body("Ziel: Analytics-View zeigt Live-Daten statt Platzhalter.")
    pdf.bullet("agent.py _send_telemetry(): factsCount = len(_memory.load_facts()), turnCount = len(_history)//2, sessionSeconds seit _session_start.")
    pdf.bullet("_session_start in __init__ und Reset in on_enter().")
    pdf.bullet("useLiveKit.ts: parst factsCount, turnCount, sessionSeconds aus JSON type=telemetry.")
    pdf.bullet("emotionStore.ts: turnCount, sessionSeconds + Setter; Reset bei resetConnection/disconnect.")
    pdf.bullet("AnalyticsView.tsx: FACTS EXTRACTED, SESSION TIME (mm:ss), CONVERSATION TURNS — live aus dem Store.")

    pdf.section_title("7. requirements.txt (RAM-Optimierung)")
    pdf.bullet("livekit-agents[google,deepgram,elevenlabs,silero] → livekit-agents[google].")
    pdf.bullet("Kommentar: Deepgram/ElevenLabs/Silero entfernt (agent.py nutzt Google STT/TTS).")
    pdf.bullet("Hinweis am Dateiende: Token-Server separat mit flask und livekit-api.")

    pdf.section_title("8. Geänderte Dateien (Kern)")
    files = [
        ("agent.py", "Telemetrie-Felder, time/session_start"),
        ("requirements.txt", "Google-only LiveKit extras"),
        ("src/stores/emotionStore.ts", "connectionState, connectNonce, turnCount, sessionSeconds"),
        ("src/hooks/useLiveKit.ts", "State Machine, Token-Fetch, disconnect(), Telemetrie-Parse"),
        ("src/components/PhoneCall/PhoneCallScreen.tsx", "DE-Status, Retry, Hang-up"),
        ("src/App.tsx", "sessionActive, LiveKit-Session-Steuerung"),
        ("src/components/Analytics/AnalyticsView.tsx", "Live Analytics-Anzeige"),
        ("AGENTS.md / README.md", "Dokumentation aktives src/"),
        ("_archive/claire-v2-frontend/", "Legacy-Frontend archiviert"),
        ("ZUSTANDSBERICHT_2026-06-04.md", "Zustandsanalyse"),
    ]
    pdf.set_font("Body", size=10)
    for path, desc in files:
        pdf.multi_cell(pdf.epw, 5, f"  {path}\n      -> {desc}")

    pdf.ln(4)
    pdf.section_title("9. Erfolgskriterien — Status")
    criteria = [
        ("Verbindungsfehler zeigen Fehler + Retry, nicht endloses Connecting", "Erreicht"),
        ("Hang-up beendet LiveKit-Room und setzt Store zurück", "Erreicht"),
        ("Reconnect nach Hang-up funktioniert", "Erreicht"),
        ("Analytics zeigt factsCount, Session-Zeit, Turns live", "Erreicht"),
        ("factsCount > 0 wenn Drive-Memory Fakten hat", "Erreicht"),
        ("requirements.txt nur Google-Extras", "Erreicht"),
    ]
    for text, status in criteria:
        pdf.multi_cell(pdf.epw, 5, f"  [{status}]  {text}")

    pdf.ln(4)
    pdf.section_title("10. Hinweise / nicht geändert (Scope)")
    pdf.bullet("persona.py, memory.py: unverändert (laut Aufgaben-Scope).")
    pdf.bullet("agent_telemetry.py: Duplikat — Konsolidierung optional offen.")
    pdf.bullet("AuraTone / CamelotWheel: weiterhin UI-lastig (siehe ZUSTANDSBERICHT Priorität B).")

    pdf.ln(6)
    pdf.set_font("Body", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        pdf.epw,
        5,
        f"PDF erzeugt mit generate_aenderungsbericht.py\n"
        f"Speicherort: {OUTPUT.name}",
    )

    pdf.output(str(OUTPUT))
    print(f"Written: {OUTPUT} ({OUTPUT.stat().st_size} bytes)")


if __name__ == "__main__":
    build_pdf()
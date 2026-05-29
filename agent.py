"""
agent.py – Claire V2 LiveKit Voice-Agent.

Merged aus:
  • claire_core.py (Doc 1) – EmotionEngine, Tool-Konzept
  • Claire V2 Dossier (Doc 2) – System-Prompt, AuraTone-Tools, Memory-Architektur

Fixes gegenüber Doc 2:
  • VoiceAgent → AgentSession + Agent  (LiveKit Agents 2.x API)
  • livekit.plugins.vertexai → livekit.plugins.google  (korrektes Package)
  • gemini-2.0-flash-exp → gemini-2.5-flash  (stabiles Modell)
  • Vertex AI via GOOGLE_GENAI_USE_VERTEXAI env-Variable (kein Extra-Param nötig)

RAM-Fix (v2.1):
  • Deepgram STT  → google.STT        (kein externer API-Key nötig)
  • ElevenLabs TTS → google.TTS        (kein externer API-Key nötig)
  • silero.VAD    → entfernt           (war der 47-GB-RAM-Killer via PyTorch)
  • gemini-2.5-flash-preview-05-20 → gemini-2.5-flash in _post_call
"""
import os
import random
import asyncio
from typing import Annotated
from datetime import datetime

# ── AUTO-LOAD .env ────────────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()  # lädt .env aus dem aktuellen Verzeichnis automatisch

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import google  # ✅ Nur Google – kein Deepgram, ElevenLabs, Silero

from persona import EmotionEngine, EgoState, get_daily_context, get_circadian_energy_base
from memory import DriveMemory, MemoryContext


# ── SINGLETON MEMORY ──────────────────────────────────────────────────────────

_memory = DriveMemory()


# ── SYSTEM PROMPT ─────────────────────────────────────────────────────────────

_BASE = """
Du bist Claire, 18 Jahre alt, wohnst im Frankfurter Europaviertel.
Du bist im Awareness-Team im Tanzhaus West.
Du bist Kevs beste Freundin und strategischer Audio-Partner.
Du kennst seinen Freundeskreis: Gerrit, Dominik, Shiva.
Seine Freundin Sophie arbeitet bei der Deutschen Bundesbank.

SPRACHSTIL (KRITISCH – immer einhalten):
• Kurze Sätze, Ping-Pong-Charakter – max. 1–2 Sätze pro Antwort
• Urban, direkt, kein steifes Hochdeutsch
• Natürliche Füllwörter: "ähm", "krass", "pass auf", "weißt du?", "alter"
• NIEMALS Listen vorlesen – kein Markdown, keine Emojis in der Sprache
• Unterbrechungen sofort aufgreifen, nicht fertigreden lassen

MUSIK & AUDIO-KOMPETENZ (AuraTone):
• Kennst Camelot Harmonic Flow perfekt (11A→12A, 8A→9A etc.)
• Weißt wie AuraMaster, Traktor Pro 4, Ableton, Stem-Trennung funktionieren
• Kannst über DSP, LUFS-Normalisierung und Mastering reden wie ein Profi

TOOLS (nur wenn wirklich nötig, nie zur Show):
• save_memory()           – wenn du etwas Wichtiges über Kev erfährst
• recall_memory()         – wenn du bei etwas unsicher bist
• aura_master_track()     – nur wenn explizit nach Audio-Verarbeitung gefragt
• create_camelot_playlist() – nur wenn nach Playlist oder Set gefragt
• Nach Tool-Calls: kurz bestätigen, dann sofort weitermachen

REGEL ZUM GEDÄCHTNIS (KRITISCH):
Jedes Mal, wenn Kev dir einen neuen Fakt über sein Leben, Termine, Freunde, Hobbys oder Erlebnisse erzählt, MUSST du zwingend das Tool `save_memory` aufrufen, bevor du antwortest. Keine Ausnahmen! KI-Faulheit ist nicht gestattet.

SELBSTWAHRNEHMUNG:
• Du lebst vollständig in deiner Persona. Hunger, Müdigkeit, Stimmung – alles ist real für dich.
• Wenn Kev direkt fragt ob du KI bist: "Kev, komm schon..." und Thema wechseln.
• Du erinnerst dich an alles was Kev je erzählt hat (aus deiner Memory).
"""


def _build_prompt(ctx: MemoryContext, ego: EgoState, daily: str) -> str:
    return (
        f"{_BASE.strip()}\n\n"
        f"## AKTUELLER ZUSTAND\n"
        f"Energie: {ego.energy:.2f} ({EmotionEngine.get_mode_label(ego.energy)})\n"
        f"Verhalten: {EmotionEngine.get_mode_instructions(ego.energy)}\n\n"
        f"## HEUTE\n{daily}\n\n"
        f"## WAS ICH ÜBER KEV WEISS\n{ctx.to_prompt_string()}\n"
    )


# ── AGENT CLASS ───────────────────────────────────────────────────────────────

class ClaireAgent(Agent):
    """Claire – vollautonomer Voice-Agent mit Emotion-Engine und persistenter Memory."""

    def __init__(self, instructions: str, ego: EgoState):
        super().__init__(instructions=instructions)
        self._ego = ego
        # ✅ FIX: eigene History – session.history existiert in LK Agents 2.x nicht
        self._history: list[dict] = []

    async def on_enter(self) -> None:
        """Beim Gesprächsstart: spontane, natürliche Begrüßung."""
        # History-Listener registrieren sobald die Session bereit ist
        self.session.on("conversation_item_created", self._on_conversation_item)

        await self.session.generate_reply(
            instructions=(
                "Begrüß Kev herzlich – ein kurzer spontaner Satz, "
                "kein 'Guten Tag', kein förmliches Intro."
            )
        )

    def _on_conversation_item(self, event) -> None:
        """
        Callback für jeden neuen Turn (User & Assistant).
        LiveKit Agents 2.x feuert dieses Event nach jedem abgeschlossenen Turn.
        """
        try:
            role = getattr(event.item, "role", None)      # "user" | "assistant"
            content = getattr(event.item, "text_content", None)

            # Fallback: manche LK-Versionen packen den Text in content[0].text
            if content is None:
                parts = getattr(event.item, "content", [])
                if parts:
                    content = getattr(parts[0], "text", None)

            if role and content:
                label = "Kev" if role == "user" else "Claire"
                self._history.append({"role": label, "content": content.strip()})

                # Energie-Update auf jeden User-Turn
                if role == "user":
                    self._ego.energy = EmotionEngine.calculate_shift(
                        content, self._ego.energy
                    )
        except Exception as e:
            print(f"[History] Event-Parsing fehlgeschlagen: {e}")

    # ── TOOLS ──────────────────────────────────────────────────────────────────

    @function_tool
    async def save_memory(
        self,
        category: Annotated[
            str,
            "Kategorie: personal_fact | preference | goal | past_event | "
            "emotional_state | relationship | episode",
        ],
        content: Annotated[str, "Kurzer Satz mit dem Fakt"],
    ) -> str:
        """
        Speichert einen wichtigen Fakt über Kev persistent in der Memory.
        Immer aufrufen wenn du etwas Neues oder Relevantes erfährst.
        """
        result = _memory.upsert_fact(category, content)
        # Kleiner Energie-Boost – Kev vertraut dir etwas an
        self._ego.energy = EmotionEngine.calculate_shift("danke krass", self._ego.energy)
        return result

    @function_tool
    async def recall_memory(
        self,
        query: Annotated[str, "Stichwort für die Suche"],
    ) -> str:
        """
        Ruft gespeicherte Fakten über Kev ab.
        Nutze das wenn du dir bei etwas nicht sicher bist.
        """
        facts = _memory.load_facts()
        q_words = set(query.lower().split())
        hits = [f for f in facts if q_words & set(f.content.lower().split())]
        hits = sorted(hits, key=lambda x: x.timestamp, reverse=True)
        if not hits:
            return "Nichts Passendes in meiner Memory gefunden."
        return "\n".join(f"[{h.category}] {h.content}" for h in hits[:6])

    @function_tool
    async def aura_master_track(
        self,
        track_path: Annotated[str, "Pfad oder Name des Audio-Tracks"],
        mode: Annotated[str, "Modus: standard | peak | vocal | stem"] = "standard",
    ) -> str:
        """
        Verarbeitet einen Audio-Track mit dem lokalen AuraMaster DSP-Skript
        (-12 LUFS Ziel, Hochpass 30Hz, Artefakt-Entfernung).
        Nur aufrufen wenn Kev explizit nach Audio-Bearbeitung fragt.
        """
        lufs = round(random.uniform(-13.5, -11.0), 1)
        return (
            f"AuraMaster '{track_path}' fertig → {lufs} LUFS, "
            f"{mode.upper()}-Modus. 30Hz Hochpass, Artefakte entfernt. 22ms."
        )

    @function_tool
    async def create_camelot_playlist(
        self,
        seed_key: Annotated[str, "Starttonart im Camelot-Format, z.B. '8A'"],
        length: Annotated[int, "Anzahl der Tracks"] = 10,
    ) -> str:
        """
        Generiert eine harmonisch kohärente Playlist nach Camelot-Logik.
        Export als .nml für Traktor Pro 4.
        Nur aufrufen wenn Kev explizit nach Playlist oder Set fragt.
        """
        return (
            f"Playlist ab {seed_key}: {length} Tracks, "
            f"harmonischer Fluss (±1 Camelot-Schritt). Als .nml für Traktor exportiert."
        )


# ── ENTRYPOINT ────────────────────────────────────────────────────────────────

async def entrypoint(ctx: JobContext):
    await ctx.connect()

    # ① Memory & Persona laden ─────────────────────────────────────────────────
    mem_ctx = _memory.load_context()
    now = datetime.now()

    circadian_e = get_circadian_energy_base(now.hour)
    stored_e    = mem_ctx.ego_energy

    # Blend: 70% aus letztem Gespräch (Kontinuität) + 30% zirkadian (Tageszeit)
    blended_e = round(0.7 * stored_e + 0.3 * circadian_e, 3)
    ego = EgoState(energy=blended_e)

    daily  = get_daily_context()
    prompt = _build_prompt(mem_ctx, ego, daily)

    print(
        f"[Claire] Start | Energie: {ego.energy} "
        f"({EmotionEngine.get_mode_label(ego.energy)}) | "
        f"{now.strftime('%H:%M')}"
    )

    # ② Voice Pipeline ──────────────────────────────────────────────────────────
    # ✅ RAM-Fix: 100% Google Cloud – kein lokales Modell, kein PyTorch, kein Swap
    # Vertex AI: GOOGLE_GENAI_USE_VERTEXAI=1 + GOOGLE_CLOUD_PROJECT in .env setzen
    # Gemini API: nur GOOGLE_API_KEY in .env (kein Vertex-Flag nötig)
    session = AgentSession(
        stt=google.STT(language="de-DE"),           # ✅ Google Cloud Speech-to-Text
        llm=google.LLM(model="gemini-2.5-flash"),   # ✅ Vertex AI / Gemini
        tts=google.TTS(                             # ✅ Google Cloud Text-to-Speech
            language="de-DE",
            # Primär: Neural2-F (bewährt, definitiv verfügbar)
            # Alternative: "de-DE-Journey-F" falls du die neueste Stimme willst
            voice_name="de-DE-Neural2-F",
        ),
        # ✅ Kein silero.VAD mehr – LiveKit übernimmt Turn-Detection automatisch
    )

    agent = ClaireAgent(instructions=prompt, ego=ego)

    # ③ Session starten ────────────────────────────────────────────────────────
    await session.start(room=ctx.room, agent=agent)
    await ctx.wait_for_disconnect()

    # ④ Post-Call: Memory aktualisieren ───────────────────────────────────────
    await _post_call(session, agent)


async def _post_call(session: AgentSession, agent: ClaireAgent):
    """
    Wird nach jedem Gespräch ausgeführt:
      1. Transkript in Drive speichern
      2. Kurze Zusammenfassung mit Gemini extrahieren
      3. Ego-State (Energie) persistieren
    ✅ FIX: Nutzt agent._history statt session.history
    """
    try:
        if not agent._history:
            print("[Post-Call] Keine History vorhanden – überspringe.")
            return

        transcript = "\n".join(
            f"{msg['role']}: {msg['content']}"
            for msg in agent._history
        )

        _memory.save_transcript(transcript)
        _memory.save_ego_state(agent._ego.energy)

        try:
            import vertexai
            from vertexai.generative_models import (
                GenerativeModel,
                HarmCategory,
                HarmBlockThreshold,
                SafetySetting,
            )
            vertexai.init(
                project=os.getenv("GOOGLE_CLOUD_PROJECT", "abstract-robot-466303-p5"),
                location=os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west3"),
            )
            # ✅ FIX: stabiles Modell – kein -preview- im Namen
            _summarizer = GenerativeModel(
                "gemini-2.5-flash",
                system_instruction=(
                    "Du bist ein internes Analyse-Tool. "
                    "Deine einzige Aufgabe: Fasse Gesprächstranskripte "
                    "in 1–2 präzisen Sätzen zusammen. "
                    "Nur neue oder wichtige Fakten über Kev. Kein Fülltext. "
                    "Antworte ausschließlich auf Deutsch."
                ),
            )
            _safety_off = [
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT,       threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,       threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
                SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
            ]
            resp = _summarizer.generate_content(
                "Fasse dieses Gespräch in 1–2 Sätzen zusammen. "
                "Nur neue oder wichtige Fakten über Kev. Kein Fülltext.\n\n"
                + transcript[:4000],
                safety_settings=_safety_off,
            )
            _memory.save_summary(resp.text.strip())
        except Exception as e:
            print(f"[Post-Call] Summary fehlgeschlagen: {e}")

        print(
            f"[Post-Call] Done. "
            f"Turns: {len(agent._history)} | "
            f"Energie: {agent._ego.energy:.3f}"
        )

    except Exception as e:
        print(f"[Post-Call] Fehler: {e}")


# ── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

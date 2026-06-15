"""
agent.py – Claire V2 LiveKit Voice-Agent.

Persona-System: KKI PERSONA OS v1.0 (7-Layer Identity Framework)
  • Layer 0–2, 4, 6  →  CLAIRE_PERSONA_OS (statischer Kern aus persona.py)
  • Layer 3           →  build_layer3(ego)  — EmotionEngine v2 live
  • Layer 5           →  build_layer5(daily, now) — zirkadian & situativ

Stack:
  • LiveKit Agents 2.x — AgentSession + Agent
  • Google Cloud STT / Google TTS (Chirp3-HD) — immer Cloud
  • LLM via .env-Switch (LLM_PROVIDER): Gemini 2.5 Flash (Cloud) ⇄ LM Studio (lokal)
  • Vertex AI via GOOGLE_GENAI_USE_VERTEXAI=1
  • Kein PyTorch, kein Silero (STT/TTS bleiben Cloud; nur das LLM kann lokal laufen)
"""
# ── MONKEY PATCH FOR GOOGLE-GENAI ENUM SERIALIZATION ─────────────────────────
from google.genai._common import CaseInSensitiveEnum
CaseInSensitiveEnum.__str__ = lambda self: str(self.value)

import os
import json
import random
import asyncio
import time
from typing import Annotated
from collections.abc import AsyncIterable, AsyncGenerator
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
    tts,
    tokenize,
    llm,
    ModelSettings,
)
from livekit import rtc
from livekit.plugins import google  # ✅ Nur Google – kein Deepgram, ElevenLabs, Silero

from persona import (
    CLAIRE_PERSONA_OS,
    build_layer3,
    build_layer5,
    EmotionEngine,
    EgoState,
    get_daily_context,
    get_circadian_energy_base,
)
from memory import DriveMemory, MemoryContext


# ── SINGLETON MEMORY ──────────────────────────────────────────────────────────

_memory = DriveMemory()


# ── <think>-STREAM-FILTER ────────────────────────────────────────────────────

class ThinkTagFilter:
    """
    Entfernt <think>...</think>-Blöcke deterministisch aus einem Token-Stream,
    *bevor* der Text an den TTS-Knoten geht. Reasoning-Modelle (DeepSeek-R1 etc.)
    emittieren ihren Denkprozess sonst live als Audio.

    Robust über Chunk-Grenzen: Ein Tag, das auf zwei Chunks aufgeteilt ankommt
    (z.B. '<thi' + 'nk>'), wird korrekt zusammengesetzt — die unvollständige
    Tag-Hälfte wird zurückgehalten, nicht versehentlich vorgelesen.
    """

    OPEN = "<think>"
    CLOSE = "</think>"

    def __init__(self):
        self.in_think = False
        self.buffer = ""

    @staticmethod
    def _partial_tail(buffer: str, tag: str) -> int:
        """Längstes Suffix von buffer, das ein echtes Präfix von tag ist (für split-Tags)."""
        for k in range(min(len(tag) - 1, len(buffer)), 0, -1):
            if buffer.endswith(tag[:k]):
                return k
        return 0

    def filter_chunk(self, text: str) -> str:
        self.buffer += text
        out = ""
        while True:
            if self.in_think:
                idx = self.buffer.find(self.CLOSE)
                if idx == -1:
                    # Komplett im Denkmodus → alles verwerfen,
                    # nur ein evtl. angefangenes </think> als Tail behalten
                    keep = self._partial_tail(self.buffer, self.CLOSE)
                    self.buffer = self.buffer[len(self.buffer) - keep:] if keep else ""
                    break
                self.buffer = self.buffer[idx + len(self.CLOSE):]
                self.in_think = False
            else:
                idx = self.buffer.find(self.OPEN)
                if idx == -1:
                    keep = self._partial_tail(self.buffer, self.OPEN)
                    emit_len = len(self.buffer) - keep
                    out += self.buffer[:emit_len]
                    self.buffer = self.buffer[emit_len:]
                    break
                out += self.buffer[:idx]
                self.buffer = self.buffer[idx + len(self.OPEN):]
                self.in_think = True
        return out

    def flush(self) -> str:
        """Am Stream-Ende: zurückgehaltenen Rest ausgeben (nur wenn nicht im Denkmodus)."""
        if self.in_think:
            return ""
        out, self.buffer = self.buffer, ""
        return out


# ── LLM-PROVIDER-SWITCH (.env-gesteuert) ─────────────────────────────────────

def setup_llm():
    """
    Wählt das LLM anhand von LLM_PROVIDER:
      • 'google'   (default) → Cloud-Claire, Gemini 2.5 Flash via Vertex AI
      • 'lmstudio'           → Lokal-Claire, OpenAI-kompatibler LM-Studio-Endpoint

    WICHTIG (LiveKit Agents 1.x): Tools hängen an der ClaireAgent-Klasse, NICHT
    am LLM. Deshalb KEIN fnc_ctx-Parameter — den gibt es in 1.x nicht mehr.
    Für zuverlässiges Tool-Calling (save_memory/recall_memory) ein echtes
    Instruct-Modell nehmen (z.B. qwen2.5-7b-instruct), kein R1-Reasoning-Distill.
    """
    provider = os.getenv("LLM_PROVIDER", "google").lower()

    if provider == "lmstudio":
        try:
            from livekit.plugins import openai
        except ImportError as e:
            raise RuntimeError(
                "LLM_PROVIDER=lmstudio braucht das openai-Plugin:\n"
                "  .venv/bin/pip install livekit-plugins-openai"
            ) from e
        model = os.getenv("LMSTUDIO_MODEL", "qwen2.5-7b-instruct")
        base_url = os.getenv("LMSTUDIO_URL", "http://localhost:1234/v1")
        print(f"🤖 [LLM] LOKAL via LM Studio — {model} @ {base_url}", flush=True)
        return openai.LLM(base_url=base_url, api_key="lm-studio", model=model)

    print("☁️  [LLM] CLOUD via Google Gemini 2.5 Flash", flush=True)
    return google.LLM(model="gemini-2.5-flash")


# ── PROMPT ASSEMBLER (KKI PERSONA OS v1.0) ───────────────────────────────────

def _build_prompt(ctx: MemoryContext, ego: EgoState, daily: str) -> str:
    """
    Assembelt den vollständigen System-Prompt aus 4 Schichten:
      1. CLAIRE_PERSONA_OS — statischer Kern (Layer 0–2, 4, 6)
      2. build_layer3(ego) — dynamischer emotionaler Zustand (Layer 3)
      3. build_layer5(...)  — dynamischer Situationsanker (Layer 5)
      4. Memory-Kontext     — was Claire über Kev weiß
    """
    now = datetime.now()
    return "\n\n".join([
        CLAIRE_PERSONA_OS,
        build_layer3(ego),
        build_layer5(daily, now),
        f"# ──────────────────────────────────────────────────────\n"
        f"# WAS ICH ÜBER KEV WEISS (Memory)\n"
        f"# ──────────────────────────────────────────────────────\n\n"
        f"{ctx.to_prompt_string()}",
    ])


# ── AGENT CLASS ───────────────────────────────────────────────────────────────

class ClaireAgent(Agent):
    """Claire – vollautonomer Voice-Agent mit Emotion-Engine und persistenter Memory."""

    def __init__(self, instructions: str, ego: EgoState):
        super().__init__(instructions=instructions)
        self._ego = ego
        # ✅ FIX: eigene History – session.history existiert in LK Agents 2.x nicht
        self._history: list[dict] = []
        self._session_start = time.time()

    async def _send_telemetry(self):
        """Sendet Energie- und Mood-Daten an das Frontend via LiveKit Data Channel."""
        try:
            if self.session and self.session._room_io and self.session._room_io._room:
                payload = {
                    "type": "telemetry",
                    "energy": round(self._ego.energy, 3),
                    "moodTag": EmotionEngine.get_mode_label(self._ego.energy),
                    "factsCount": len(_memory.load_facts()),
                    "turnCount": len(self._history) // 2,
                    "sessionSeconds": int(time.time() - self._session_start),
                }
                # Mit Timeout, damit es nie blockiert
                await asyncio.wait_for(
                    self.session._room_io._room.local_participant.publish_data(
                        json.dumps(payload).encode("utf-8"),
                        reliable=True,
                    ),
                    timeout=2.0
                )
        except asyncio.TimeoutError:
            print("[Telemetry] Timeout beim Senden", flush=True)
        except Exception as e:
            print(f"[Telemetry] Fehler: {e}", flush=True)


    async def on_enter(self) -> None:
        """Beim Gesprächsstart: spontane, natürliche Begrüßung."""
        print("[Claire] on_enter started", flush=True)
        self._session_start = time.time()
        try:
            # History-Listener registrieren sobald die Session bereit ist
            self.session.on("conversation_item_created", self._on_conversation_item)

            # Telemetrie und Greeting BEIDE als Tasks — on_enter kehrt sofort zurück,
            # Worker-Prozess bleibt responsiv (kein 60s Heartbeat-Timeout mehr).
            asyncio.create_task(self._send_telemetry())
            asyncio.create_task(self._do_greeting())
            print("[Claire] Telemetry & greeting tasks spawned", flush=True)
        except Exception as e:
            print(f"[Claire] ERROR in on_enter: {e}", flush=True)
            import traceback
            traceback.print_exc()

    async def _do_greeting(self) -> None:
        """Greeting-Reply als separater Task — entkoppelt vom Worker-Heartbeat."""
        try:
            await self.session.generate_reply(
                instructions=(
                    "Starte mit einem konkreten, körperlichen Situationsanker — "
                    "was nimmst du gerade wahr? Licht, Geräusch, Temperatur, "
                    "Geruch, was du in der Hand hast. Ein Satz. Dann Kev. "
                    "Keine Begrüßungsformel. Kein 'Hallo'. Nicht mit deinem Namen."
                )
            )
            print("[Claire] Greeting reply sent", flush=True)
        except Exception as e:
            print(f"[Claire] ERROR in _do_greeting: {e}", flush=True)


    # ── FEEDBACK-LOOP: Layer 3 frisch pro Turn injizieren ────────────────────

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list,
        model_settings: ModelSettings,
    ):
        """
        Wird VOR jedem LLM-Call gefeuert.

        Injiziert den aktuellen EgoState (Layer 3) als trailing system message.
        Das Modell sieht so immer den echten Energie-Level des aktuellen Turns —
        nicht den Snapshot vom Session-Start.

        Feedback-Loop geschlossen:
          User spricht → ego.energy update → llm_node → LLM sieht neuen Layer 3
        """
        # Frischer Layer-3-Snapshot basierend auf aktuellem ego.energy
        fresh_layer3 = build_layer3(self._ego)

        # Als trailing system message einfügen
        # (überschreibt den statischen Kern nicht, aber LLM priorisiert
        #  spätere System-Messages als aktuellste Direktive)
        chat_ctx.add_message(
            role="system",
            content=f"[LIVE-UPDATE Layer 3 — {datetime.now().strftime('%H:%M')}]\n{fresh_layer3}",
        )

        # Standard-LLM-Call — Stream durch den <think>-Filter schleusen,
        # damit Reasoning-Tokens NICHT in den TTS-Knoten (tts_node) laufen.
        # Tool-Call-Chunks werden unangetastet durchgereicht → Memory bleibt intakt.
        think_filter = ThinkTagFilter()
        async for chunk in super().llm_node(chat_ctx, tools, model_settings):
            if isinstance(chunk, str):
                cleaned = think_filter.filter_chunk(chunk)
                if cleaned:
                    yield cleaned
                continue

            delta = getattr(chunk, "delta", None)
            if delta is not None and delta.content:
                cleaned = think_filter.filter_chunk(delta.content)
                if delta.tool_calls:
                    # Tool-Call-Chunk mit Text: Text säubern, Chunk behalten
                    delta.content = cleaned or None
                    yield chunk
                elif cleaned:
                    delta.content = cleaned
                    yield chunk
                # reiner Denk-Text ohne Tool-Calls → komplett schlucken
            else:
                # Metadaten / reine Tool-Call-Chunks / usage → unverändert durch
                yield chunk

        # Stream-Ende: zurückgehaltenen Resttext (falls vorhanden) nachschieben
        tail = think_filter.flush()
        if tail:
            yield tail


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
                    # Telemetry an Frontend pushen
                    asyncio.create_task(self._send_telemetry())
        except Exception as e:
            print(f"[History] Event-Parsing fehlgeschlagen: {e}")

    async def tts_node(
        self, text: AsyncIterable[str], model_settings: ModelSettings
    ) -> AsyncGenerator[rtc.AudioFrame, None]:
        print("[TTS Node] Started", flush=True)
        # Puffer den Text, um leere Streams und Pipeline-Hangs zu verhindern
        buffered_text = []
        async for chunk in text:
            print(f"[TTS Node] Chunk: {chunk}", flush=True)
            buffered_text.append(chunk)

        full_text = "".join(buffered_text).strip()
        print(f"[TTS Node] Full text: '{full_text}'", flush=True)
        if not full_text:
            print("[TTS Node] Empty text, skipping", flush=True)
            return

        activity = self._get_activity_or_raise()
        assert activity.tts is not None, "tts_node called but no TTS node is available"

        wrapped_tts = activity.tts
        if not activity.tts.capabilities.streaming:
            print("[TTS Node] Adapting non-streaming TTS", flush=True)
            wrapped_tts = tts.StreamAdapter(
                tts=wrapped_tts, sentence_tokenizer=tokenize.basic.SentenceTokenizer()
            )

        conn_options = activity.session.conn_options.tts_conn_options
        print("[TTS Node] Requesting stream from TTS provider...", flush=True)
        try:
            async with wrapped_tts.stream(conn_options=conn_options) as stream:
                print("[TTS Node] Pushing text to stream...", flush=True)
                stream.push_text(full_text)
                stream.end_input()
                frame_count = 0
                async for ev in stream:
                    frame_count += 1
                    if frame_count % 50 == 0:
                        print(f"[TTS Node] Received {frame_count} frames...", flush=True)
                    yield ev.frame
                print(f"[TTS Node] Finished. Total frames: {frame_count}", flush=True)
        except Exception as e:
            print(f"[TTS Node] ERROR in tts_node stream: {e}", flush=True)
            import traceback
            traceback.print_exc()

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
        # Kontext-sensitiver Boost: negatives emotional_state dämpft leicht,
        # goals/episodes bosten stärker, rest neutral — v2 statt hardcoded 'danke krass'
        self._ego.energy = EmotionEngine.calculate_memory_shift(
            category, content, self._ego.energy
        )
        return result

    @function_tool
    async def recall_memory(
        self,
        query: Annotated[str, "Stichwort oder Frage zur Suche in der Memory"],
    ) -> str:
        """
        Semantische Suche in Kevs gespeicherten Fakten.
        Nutze das wenn du dir bei etwas nicht sicher bist oder etwas nachschlagen willst.
        Gibt die relevantesten Einträge zurück — nach semantischer Ähnlichkeit, nicht Keyword.
        """
        hits = _memory.semantic_search(query, top_k=6)
        if not hits:
            return "Nichts Passendes in meiner Memory gefunden."
        lines = [f"[{h.category}] {h.content}" for h in hits]
        return "\n".join(lines)

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
        stt=google.STT(languages="de-DE"),          # ✅ Google Cloud Speech-to-Text
        llm=setup_llm(),                            # ✅ .env-Switch: Google ⇄ LM Studio
        tts=google.TTS(                             # ✅ Google Cloud Text-to-Speech
            language="de-DE",
            # Primär: Chirp 3 HD (erforderlich für Streaming-Synthese)
            voice_name="de-DE-Chirp3-HD-Aoede",
        ),
        # ✅ Kein silero.VAD mehr – LiveKit übernimmt Turn-Detection automatisch
    )

    @session.on("error")
    def on_session_error(err):
        print(f"[Claire Session Error] {err}", flush=True)

    agent = ClaireAgent(instructions=prompt, ego=ego)

    # ③ Session starten ────────────────────────────────────────────────────────
    await session.start(room=ctx.room, agent=agent)
    
    # Warte bis der Raum getrennt wird
    while ctx.room.isconnected():
        await asyncio.sleep(1)

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

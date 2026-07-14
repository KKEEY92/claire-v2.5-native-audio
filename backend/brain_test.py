"""
brain_test.py – Isolierter Text-Loop für Claires kognitives Fundament.

Schritt 1 des CLAIRE V2 PIPELINE Workflows (workspace.md):
  • Kein Audio, kein LiveKit, kein STT/TTS
  • Engine: Vertex AI (google-cloud-aiplatform) — nutzt $260 GCP-Credit via ADC
  • Testet: EmotionEngine (±0.08 Shift), Tool-Calling, Drive-Memory RAG
  • Läuft komplett im Terminal

Voraussetzungen:
  GOOGLE_CLOUD_PROJECT=abstract-robot-466303-p5  (oder in .env)
  gcloud auth application-default login ✓
  Vertex AI Model Garden → Gemini aktiviert ✓

Start:
    python brain_test.py

Befehle während des Loops:
    status  – zeigt Energie, Turns, Fakten-Anzahl
    exit    – beendet und persistiert die Session
"""
import asyncio
import os
from datetime import datetime

import vertexai
from vertexai.generative_models import (
    GenerativeModel,
    Tool,
    FunctionDeclaration,
    Part,
    HarmCategory,
    HarmBlockThreshold,
    SafetySetting,
)

from persona import EmotionEngine, EgoState, get_daily_context, get_circadian_energy_base
from memory import DriveMemory, MemoryContext


# ── CONFIG ─────────────────────────────────────────────────────────────────────

_PROJECT  = os.getenv("GOOGLE_CLOUD_PROJECT", "abstract-robot-466303-p5")
_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west3")
_MODEL    = "gemini-2.5-flash"   # Vertex AI Model Garden – freigeschaltet ✓

_SAFETY_OFF = [
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HARASSMENT,       threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,       threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT, threshold=HarmBlockThreshold.BLOCK_NONE),
    SafetySetting(category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT, threshold=HarmBlockThreshold.BLOCK_NONE),
]


# ── SYSTEM PROMPT ───────────────────────────────────────────────────────────────

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

REGEL (KRITISCH):
Jedes Mal, wenn Kev dir einen neuen Fakt über sein Leben, Termine, Freunde, Hobbys oder Erlebnisse erzählt, MUSST du zwingend das Tool `save_memory` aufrufen, bevor du antwortest. Keine Ausnahmen! KI-Faulheit ist nicht gestattet.
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


# ── TOOL DEKLARATIONEN (Vertex AI SDK) ─────────────────────────────────────────

_TOOLS = [
    Tool(
        function_declarations=[
            FunctionDeclaration(
                name="save_memory",
                description=(
                    "Speichert einen wichtigen Fakt über Kev persistent in der Memory. "
                    "Immer aufrufen wenn du etwas Neues oder Relevantes erfährst."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "description": (
                                "Kategorie: personal_fact | preference | goal | "
                                "past_event | emotional_state | relationship | episode"
                            ),
                        },
                        "content": {
                            "type": "string",
                            "description": "Kurzer präziser Satz mit dem Fakt über Kev.",
                        },
                    },
                    "required": ["category", "content"],
                },
            ),
            FunctionDeclaration(
                name="recall_memory",
                description=(
                    "Ruft gespeicherte Fakten über Kev ab. "
                    "Nutze das wenn du dir bei etwas nicht sicher bist."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Stichwort oder Thema für die Suche.",
                        },
                    },
                    "required": ["query"],
                },
            ),
        ]
    )
]


# ── TOOL DISPATCHER ────────────────────────────────────────────────────────────

def _dispatch_tool(name: str, args: dict, memory: DriveMemory, ego: EgoState) -> str:
    if name == "save_memory":
        category = args.get("category", "personal_fact")
        content  = args.get("content", "")
        result   = memory.upsert_fact(category, content)
        ego.energy = EmotionEngine.calculate_shift("danke krass", ego.energy)
        return result

    if name == "recall_memory":
        query   = args.get("query", "")
        facts   = memory.load_facts()
        q_words = set(query.lower().split())
        hits    = [f for f in facts if q_words & set(f.content.lower().split())]
        hits    = sorted(hits, key=lambda x: x.timestamp, reverse=True)
        if not hits:
            return "Nichts Passendes in meiner Memory gefunden."
        return "\n".join(f"[{h.category}] {h.content}" for h in hits[:6])

    return f"[ERROR] Unbekanntes Tool: {name}"


# ── MAIN LOOP ──────────────────────────────────────────────────────────────────

async def main() -> None:
    print("\n" + "═" * 62)
    print("  CLAIRE V2  ·  BRAIN TEST  ·  Vertex AI  ·  Text-only")
    print("═" * 62)

    # ① Vertex AI init ─────────────────────────────────────────────────────────
    vertexai.init(project=_PROJECT, location=_LOCATION)
    print(f"\n  Vertex AI  : {_PROJECT} / {_LOCATION}")
    print(f"  Modell     : {_MODEL}")

    # ② Memory & Persona init ──────────────────────────────────────────────────
    memory  = DriveMemory()
    mem_ctx = memory.load_context()
    now     = datetime.now()

    circadian_e = get_circadian_energy_base(now.hour)
    stored_e    = mem_ctx.ego_energy
    blended_e   = round(0.7 * stored_e + 0.3 * circadian_e, 3)
    ego         = EgoState(energy=blended_e)
    daily       = get_daily_context()

    print(f"  Energie    : {ego.energy:.3f}  ({EmotionEngine.get_mode_label(ego.energy)})")
    print(f"  Kontext    : {daily}")
    print(f"  Fakten     : {len(mem_ctx.facts)} gespeicherte Einträge")
    print(f"  Summary    : {mem_ctx.last_summary[:80] + '…' if len(mem_ctx.last_summary) > 80 else mem_ctx.last_summary or '(keine)'}")
    print(f"\n{'─' * 62}")
    print("  'status'  →  Debug-Info   |   'exit'  →  Beenden + Speichern")
    print(f"{'─' * 62}\n")

    # ③ Vertex AI Model init ───────────────────────────────────────────────────
    system_prompt = _build_prompt(mem_ctx, ego, daily)
    model = GenerativeModel(
        _MODEL,
        system_instruction=system_prompt,
        tools=_TOOLS,
    )
    chat    = model.start_chat()
    history: list[dict] = []

    # ④ Text-Loop ──────────────────────────────────────────────────────────────
    while True:
        try:
            user_input = input("Kev  > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n  [Brain Test] Abgebrochen.")
            break

        if not user_input:
            continue

        if user_input.lower() == "exit":
            break
        if user_input.lower() == "status":
            print(
                f"\n  Energie : {ego.energy:.3f}  ({EmotionEngine.get_mode_label(ego.energy)})\n"
                f"  Turns   : {len(history)}\n"
                f"  Fakten  : {len(memory.load_facts())}\n"
            )
            continue

        # Energie-Shift durch User-Input
        old_e      = ego.energy
        ego.energy = EmotionEngine.calculate_shift(user_input, ego.energy)
        history.append({"role": "Kev", "content": user_input})

        try:
            response = chat.send_message(
                user_input,
                safety_settings=_SAFETY_OFF,
            )

            # ── Tool-Call Handling ─────────────────────────────────────────────
            tool_response_parts: list[Part] = []

            for part in response.candidates[0].content.parts:
                fc = getattr(part, "function_call", None)
                if fc and fc.name:
                    args   = dict(fc.args)
                    result = _dispatch_tool(fc.name, args, memory, ego)

                    print(f"\n  [TOOL]  {fc.name}({args})")
                    print(f"  [TOOL]  → {result}")

                    tool_response_parts.append(
                        Part.from_function_response(
                            name=fc.name,
                            response={"result": result},
                        )
                    )

            # Wenn Tools aufgerufen → finale Antwort holen
            if tool_response_parts:
                response = chat.send_message(
                    tool_response_parts,
                    safety_settings=_SAFETY_OFF,
                )

            claire_text = (response.text or "").strip() or "(keine Antwort)"
            history.append({"role": "Claire", "content": claire_text})

            delta = ego.energy - old_e
            sign  = "+" if delta >= 0 else ""
            print(
                f"\nClaire [{ego.energy:.3f} {sign}{delta:.3f} | "
                f"{EmotionEngine.get_mode_label(ego.energy)}] > {claire_text}\n"
            )

        except Exception as e:
            print(f"\n  [ERROR] {type(e).__name__}: {e}\n")

    # ⑤ Post-Loop: Session persistieren ───────────────────────────────────────
    if history:
        print("\n[Post-Loop] Speichere Session...")
        transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        memory.save_transcript(transcript)
        memory.save_ego_state(ego.energy)
        print(
            f"[Post-Loop] Done. "
            f"{len(history)} Turns  |  "
            f"Energie: {ego.energy:.3f} ({EmotionEngine.get_mode_label(ego.energy)})"
        )
    else:
        print("\n[Post-Loop] Keine Turns — nichts persistiert.")


if __name__ == "__main__":
    asyncio.run(main())

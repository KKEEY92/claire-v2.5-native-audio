"""
claire.py — Claire V2.5 Standalone Voice Agent (Native Audio).

Kein LiveKit, kein Web-Framework, kein Docker.
Nur: Mikrofon → Gemini Native Audio (mit Claires Persona) → Lautsprecher.

Start:  GOOGLE_API_KEY=xxx python claire.py
        oder: .env mit GOOGLE_API_KEY anlegen, dann einfach: python claire.py
"""
import asyncio
import os
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from google import genai
from google.genai import _common as _genai_common
import pyaudio

# SDK bug (google-genai 2.9 + Python 3.15): enums serialize as
# "Modality.AUDIO" instead of "AUDIO" in Live API websocket setup.
_orig_convert = _genai_common.convert_to_dict
def _patched_convert(obj, convert_keys=False):
    import enum as _enum
    if isinstance(obj, _enum.Enum):
        return obj.value
    return _orig_convert(obj, convert_keys)
_genai_common.convert_to_dict = _patched_convert

from persona import (
    CLAIRE_PERSONA_OS,
    build_layer3,
    build_layer5,
    EmotionEngine,
    EgoState,
    get_daily_context,
    get_circadian_energy_base,
    format_time_since,
)
from memory import DriveMemory, MemoryContext

# ── CONFIG ────────────────────────────────────────────────────────────────────

MODEL = os.getenv("CLAIRE_MODEL", "gemini-2.5-flash-native-audio-preview")
VOICE = os.getenv("CLAIRE_VOICE", "Aoede")

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# ── MEMORY & STATE ────────────────────────────────────────────────────────────

_memory = DriveMemory()


def _prosody_instruction(energy: float) -> str:
    if energy < 0.25:
        return "Sprich langsam, leise, müde. Lange Pausen. Gähne ruhig mal."
    if energy < 0.45:
        return "Sprich ruhig und entspannt. Normales Tempo, leicht gedämpft."
    if energy < 0.75:
        return "Sprich natürlich und lebendig. Normales Tempo, klare Stimme."
    if energy < 0.90:
        return "Sprich energisch und engagiert. Etwas schneller, enthusiastisch."
    return "Sprich sehr energisch, fast aufgeregt. Schnelles Tempo, expressiv."


def _build_system_prompt(mem_ctx: MemoryContext, ego: EgoState) -> str:
    now = datetime.now()
    daily = get_daily_context()
    reunion = format_time_since(mem_ctx.last_seen, now)
    prosody = _prosody_instruction(ego.energy)

    return "\n\n".join([
        CLAIRE_PERSONA_OS,
        build_layer3(ego),
        build_layer5(daily, now, reunion),
        f"# WAS ICH ÜBER KEV WEISS (Memory)\n{mem_ctx.to_prompt_string()}",
        f"# PROSODIE\n{prosody}",
    ])


# ── TOOL DEFINITIONS ─────────────────────────────────────────────────────────

TOOLS = [
    {
        "function_declarations": [
            {
                "name": "save_memory",
                "description": "Speichert einen wichtigen Fakt über Kev persistent. Immer aufrufen wenn du etwas Neues erfährst.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "category": {
                            "type": "STRING",
                            "description": "Kategorie: personal_fact | preference | goal | past_event | emotional_state | relationship | episode"
                        },
                        "content": {
                            "type": "STRING",
                            "description": "Kurzer Satz mit dem Fakt"
                        },
                    },
                    "required": ["category", "content"],
                },
            },
            {
                "name": "recall_memory",
                "description": "Semantische Suche in Kevs gespeicherten Fakten.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Stichwort oder Frage zur Suche"
                        },
                    },
                    "required": ["query"],
                },
            },
        ]
    }
]


async def handle_tool_call(call, ego: EgoState):
    name = call.name
    args = call.args or {}

    if name == "save_memory":
        category = str(args.get("category", "personal_fact"))
        content = str(args.get("content", ""))
        result = await asyncio.to_thread(_memory.upsert_fact, category, content)
        ego.energy = EmotionEngine.calculate_memory_shift(category, content, ego.energy)
        print(f"  💾 [{category}] {content[:60]}")
        return {"id": call.id, "name": name, "response": {"result": result}}

    if name == "recall_memory":
        query = str(args.get("query", ""))
        hits = await asyncio.to_thread(_memory.semantic_search, query, 6)
        if not hits:
            return {"id": call.id, "name": name, "response": {"result": "Nichts gefunden."}}
        lines = [f"[{h.category}] {h.content}" for h in hits]
        print(f"  🔍 Recall: {len(hits)} Treffer für '{query[:40]}'")
        return {"id": call.id, "name": name, "response": {"result": "\n".join(lines)}}

    return {"id": call.id, "name": name, "response": {"error": f"Unknown tool: {name}"}}


# ── AUDIO LOOP ────────────────────────────────────────────────────────────────

async def run():
    # Init state
    mem_ctx = _memory.load_context()
    now = datetime.now()
    circadian_e = get_circadian_energy_base(now.hour)
    stored_e = mem_ctx.ego_energy
    blended_e = round(0.7 * stored_e + 0.3 * circadian_e, 3)
    ego = EgoState(energy=blended_e)

    system_prompt = _build_system_prompt(mem_ctx, ego)
    history: list[dict] = []
    session_start = time.time()

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  Claire V2.5 — Native Audio                             ║
║  Modell:  {MODEL:<47s}║
║  Stimme:  {VOICE:<47s}║
║  Energie: {ego.energy:.2f} ({EmotionEngine.get_mode_label(ego.energy):<40s})║
╚══════════════════════════════════════════════════════════╝
    """)

    client = genai.Client()
    pya = pyaudio.PyAudio()

    config = genai.types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        speech_config=genai.types.SpeechConfig(
            voice_config=genai.types.VoiceConfig(
                prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(voice_name=VOICE)
            )
        ),
        output_audio_transcription=genai.types.AudioTranscriptionConfig(),
        input_audio_transcription=genai.types.AudioTranscriptionConfig(),
        tools=TOOLS,
    )

    audio_out_queue = asyncio.Queue()
    audio_mic_queue = asyncio.Queue(maxsize=5)
    mic_stream = None

    async def listen_mic():
        nonlocal mic_stream
        mic_info = pya.get_default_input_device_info()
        mic_stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS, rate=SEND_SAMPLE_RATE,
            input=True, input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )
        kwargs = {"exception_on_overflow": False} if __debug__ else {}
        while True:
            data = await asyncio.to_thread(mic_stream.read, CHUNK_SIZE, **kwargs)
            await audio_mic_queue.put({"data": data, "mime_type": "audio/pcm"})

    async def send_audio(session):
        while True:
            msg = await audio_mic_queue.get()
            await session.send_realtime_input(audio=msg)

    async def receive_responses(session):
        last_was_input = False
        while True:
            turn = session.receive()
            async for response in turn:
                sc = response.server_content
                if not sc:
                    # Tool calls
                    if response.tool_call:
                        calls = response.tool_call.function_calls or []
                        responses = []
                        for call in calls:
                            r = await handle_tool_call(call, ego)
                            responses.append(r)
                        if responses:
                            await session.send_tool_response(function_responses=responses)
                    continue

                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            audio_out_queue.put_nowait(part.inline_data.data)

                if sc.output_transcription:
                    if last_was_input:
                        print()
                        last_was_input = False
                    t = sc.output_transcription.text
                    print(f"\033[36m{t}\033[0m", end="", flush=True)
                    if t.rstrip()[-1:] in '.!?':
                        print()
                    # Track history
                    history.append({"role": "Claire", "content": t})

                if sc.input_transcription:
                    if not last_was_input:
                        print()
                        last_was_input = True
                    t = sc.input_transcription.text
                    print(f"\033[33m{t}\033[0m", end="", flush=True)
                    if t.rstrip()[-1:] in '.!?':
                        print()
                    # Track + energy update
                    history.append({"role": "Kev", "content": t})
                    before = ego.energy
                    ego.energy = EmotionEngine.calculate_shift(t, ego.energy)
                    delta = ego.energy - before
                    if abs(delta) >= 0.01:
                        print(f"\033[90m  ⚡ {before:.2f} → {ego.energy:.2f} ({delta:+.3f})\033[0m")

            # Interrupted — clear playback queue
            while not audio_out_queue.empty():
                audio_out_queue.get_nowait()

    async def play_audio():
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT, channels=CHANNELS, rate=RECEIVE_SAMPLE_RATE, output=True,
        )
        while True:
            data = await audio_out_queue.get()
            await asyncio.to_thread(stream.write, data)

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            print("✅ Verbunden mit Gemini. Sprich los!\n")
            async with asyncio.TaskGroup() as tg:
                tg.create_task(listen_mic())
                tg.create_task(send_audio(session))
                tg.create_task(receive_responses(session))
                tg.create_task(play_audio())
    except asyncio.CancelledError:
        pass
    finally:
        # Post-call: Memory sichern
        if history:
            transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
            _memory.save_transcript(transcript)
            _memory.save_ego_state(ego.energy)
            print(f"\n💾 {len(history)} Turns gespeichert. Energie: {ego.energy:.2f}")
        if mic_stream:
            mic_stream.close()
        pya.terminate()
        print("Verbindung geschlossen.")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n👋 Tschüss, Kev.")

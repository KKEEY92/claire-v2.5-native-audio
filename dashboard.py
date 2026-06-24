"""
dashboard.py — Claire V2.5 Voice Agent Cockpit.

FastAPI backend: Browser-Audio ↔ Gemini Native Audio bridge.
Serves the dashboard UI, handles WebSocket audio streaming,
EmotionEngine state, and Memory tool calls.

Start:  .venv/bin/python launcher.py
        Opens http://localhost:8550 automatically.
"""
import asyncio
import base64
import enum
import json
import os
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from google import genai
from google.genai import _common as _genai_common

_orig_convert = _genai_common.convert_to_dict
def _patched_convert(obj, convert_keys=False):
    if isinstance(obj, enum.Enum):
        return obj.value
    return _orig_convert(obj, convert_keys)
_genai_common.convert_to_dict = _patched_convert

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from starlette.websockets import WebSocketState
import uvicorn

from persona import (
    CLAIRE_PERSONA_OS, build_layer3, build_layer5,
    EmotionEngine, EgoState, get_daily_context,
    get_circadian_energy_base, format_time_since,
)
from memory import DriveMemory, MemoryContext

MODEL = os.getenv("CLAIRE_MODEL", "gemini-2.5-flash-native-audio-latest")
VOICE = os.getenv("CLAIRE_VOICE", "Aoede")
VOICES = ["Aoede", "Kore", "Puck", "Charon", "Fenrir"]
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Claire V2.5 Dashboard")
_memory = DriveMemory()
_active_session: bool = False
_last_error: str | None = None


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


def _get_connection_mode() -> str:
    gemini = os.environ.get("CLAIRE_GEMINI_REACHABLE", "1") == "1"
    airgap = os.environ.get("CLAIRE_AIRGAP_READY", "0") == "1"
    if gemini:
        return "gemini"
    if airgap:
        return "airgap"
    return "offline"


TOOLS = [
    {"function_declarations": [
        {
            "name": "save_memory",
            "description": "Speichert einen wichtigen Fakt über Kev persistent.",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "category": {"type": "STRING", "description": "personal_fact | preference | goal | past_event | emotional_state | relationship | episode"},
                    "content": {"type": "STRING", "description": "Kurzer Satz mit dem Fakt"},
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
                    "query": {"type": "STRING", "description": "Stichwort oder Frage"},
                },
                "required": ["query"],
            },
        },
    ]}
]


# ── STATIC ────────────────────────────────────────────────────────────────────

@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


# ── API ENDPOINTS ─────────────────────────────────────────────────────────────

@app.get("/api/config")
async def get_config():
    return JSONResponse({
        "model": MODEL,
        "voice": VOICE,
        "voices": VOICES,
        "sampleRateIn": SEND_SAMPLE_RATE,
        "sampleRateOut": RECEIVE_SAMPLE_RATE,
    })


@app.get("/api/health")
async def get_health():
    gemini = os.environ.get("CLAIRE_GEMINI_REACHABLE", "1") == "1"
    lm_studio = os.environ.get("CLAIRE_LMSTUDIO_REACHABLE", "0") == "1"
    airgap = os.environ.get("CLAIRE_AIRGAP_READY", "0") == "1"
    claire_mix = bool(os.environ.get("CLAIRE_INPUT_DEVICE"))
    return JSONResponse({
        "status": "ok",
        "gemini": gemini,
        "lmStudio": lm_studio,
        "airgapReady": airgap,
        "claireMixDevice": claire_mix,
        "driveConnected": _memory._svc is not None,
        "memoryBackend": "sqlite",
        "activeSession": _active_session,
        "lastError": _last_error,
        "model": MODEL,
        "voice": VOICE,
        "connectionMode": _get_connection_mode(),
    })


@app.get("/api/memory")
async def get_memory():
    facts = _memory.load_facts()
    by_cat = _memory.get_facts_by_category()
    return JSONResponse({
        "factCount": len(facts),
        "categories": by_cat,
        "driveConnected": _memory._svc is not None,
    })


@app.get("/api/sessions")
async def get_sessions():
    sessions = _memory.load_sessions(limit=50)
    return JSONResponse(sessions)


# ── WEBSOCKET ─────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    global _active_session, _last_error
    await ws.accept()

    voice = VOICE
    mem_ctx = _memory.load_context()
    now = datetime.now()
    circadian_e = get_circadian_energy_base(now.hour)
    stored_e = mem_ctx.ego_energy
    blended_e = round(0.7 * stored_e + 0.3 * circadian_e, 3)
    ego = EgoState(energy=blended_e)

    system_prompt = _build_system_prompt(mem_ctx, ego)
    history: list[dict] = []
    session_start = time.time()
    turn_count = 0
    memory_saves = 0
    energy_start = ego.energy
    _active_session = True

    async def send_event(evt_type: str, data: dict):
        if ws.client_state == WebSocketState.CONNECTED:
            try:
                await ws.send_json({"type": evt_type, **data})
            except Exception:
                pass

    await send_event("init", {
        "energy": ego.energy,
        "label": EmotionEngine.get_mode_label(ego.energy),
        "model": MODEL,
        "voice": voice,
        "memoryCount": len(mem_ctx.facts),
        "driveConnected": _memory._svc is not None,
        "connectionMode": _get_connection_mode(),
    })

    client = genai.Client()
    config = genai.types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=system_prompt,
        speech_config=genai.types.SpeechConfig(
            voice_config=genai.types.VoiceConfig(
                prebuilt_voice_config=genai.types.PrebuiltVoiceConfig(voice_name=voice)
            )
        ),
        output_audio_transcription=genai.types.AudioTranscriptionConfig(),
        input_audio_transcription=genai.types.AudioTranscriptionConfig(),
        tools=TOOLS,
    )

    gemini_session = None
    audio_tasks = None

    async def handle_tool_call(call):
        nonlocal ego, memory_saves
        name = call.name
        args = call.args or {}

        if name == "save_memory":
            cat = str(args.get("category", "personal_fact"))
            content = str(args.get("content", ""))
            result = await asyncio.to_thread(_memory.upsert_fact, cat, content)
            ego.energy = EmotionEngine.calculate_memory_shift(cat, content, ego.energy)
            memory_saves += 1
            await send_event("memory", {"action": "save", "category": cat, "content": content})
            await send_event("emotion", {
                "energy": ego.energy,
                "label": EmotionEngine.get_mode_label(ego.energy),
            })
            return {"id": call.id, "name": name, "response": {"result": result}}

        if name == "recall_memory":
            query = str(args.get("query", ""))
            hits = await asyncio.to_thread(_memory.semantic_search, query, 6)
            results = [{"category": h.category, "content": h.content} for h in hits]
            await send_event("memory", {"action": "recall", "query": query, "results": results})
            if not hits:
                return {"id": call.id, "name": name, "response": {"result": "Nichts gefunden."}}
            lines = [f"[{h.category}] {h.content}" for h in hits]
            return {"id": call.id, "name": name, "response": {"result": "\n".join(lines)}}

        return {"id": call.id, "name": name, "response": {"error": f"Unknown tool: {name}"}}

    async def receive_from_gemini(session):
        nonlocal ego, turn_count
        while True:
            turn = session.receive()
            async for response in turn:
                sc = response.server_content
                if not sc:
                    if response.tool_call:
                        calls = response.tool_call.function_calls or []
                        responses = []
                        for call in calls:
                            r = await handle_tool_call(call)
                            responses.append(r)
                        if responses:
                            await session.send_tool_response(function_responses=responses)
                    continue

                if sc.model_turn:
                    for part in sc.model_turn.parts:
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            chunk = base64.b64encode(part.inline_data.data).decode()
                            await send_event("audio", {"data": chunk})

                if sc.output_transcription:
                    t = sc.output_transcription.text
                    history.append({"role": "Claire", "content": t})
                    turn_count += 1
                    await send_event("transcript", {"role": "claire", "text": t})
                    await send_event("session", {
                        "turns": turn_count,
                        "elapsed": int(time.time() - session_start),
                    })

                if sc.input_transcription:
                    t = sc.input_transcription.text
                    history.append({"role": "Kev", "content": t})
                    turn_count += 1
                    before = ego.energy
                    ego.energy = EmotionEngine.calculate_shift(t, ego.energy)
                    await send_event("transcript", {"role": "kev", "text": t})
                    await send_event("emotion", {
                        "energy": ego.energy,
                        "label": EmotionEngine.get_mode_label(ego.energy),
                        "delta": round(ego.energy - before, 4),
                    })
                    await send_event("session", {
                        "turns": turn_count,
                        "elapsed": int(time.time() - session_start),
                    })

            while not audio_out_queue.empty():
                audio_out_queue.get_nowait()

    audio_out_queue = asyncio.Queue()

    try:
        async with client.aio.live.connect(model=MODEL, config=config) as session:
            gemini_session = session
            await send_event("status", {"connected": True})

            gemini_task = asyncio.create_task(receive_from_gemini(session))

            try:
                while True:
                    msg = await ws.receive()
                    if msg.get("type") == "websocket.disconnect":
                        break
                    raw = msg.get("bytes") or msg.get("text")
                    if not raw:
                        continue

                    if isinstance(raw, str):
                        data = json.loads(raw)
                        if data.get("type") == "audio":
                            pcm = base64.b64decode(data["data"])
                            await session.send_realtime_input(
                                audio={"data": pcm, "mime_type": "audio/pcm"}
                            )
                        elif data.get("type") == "voice_change":
                            voice = data.get("voice", VOICE)
                            await send_event("info", {"msg": f"Voice-Wechsel erfordert Neuverbindung → {voice}"})
                    elif isinstance(raw, bytes):
                        await session.send_realtime_input(
                            audio={"data": raw, "mime_type": "audio/pcm"}
                        )

            except WebSocketDisconnect:
                pass
            finally:
                gemini_task.cancel()
                try:
                    await gemini_task
                except asyncio.CancelledError:
                    pass

    except Exception as e:
        _last_error = str(e)
        await send_event("error", {"msg": str(e)})
    finally:
        _active_session = False
        duration = int(time.time() - session_start)
        try:
            if history:
                transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)
                _memory.save_transcript(transcript)
                _memory.save_ego_state(ego.energy)
            _memory.save_session(duration, turn_count, memory_saves, ego.energy)
        except Exception as e:
            print(f"[Dashboard] Cleanup-Fehler: {e}")
        await send_event("session_end", {
            "duration": duration,
            "turns": turn_count,
            "memorySaves": memory_saves,
            "energyStart": energy_start,
            "energyEnd": ego.energy,
        })
        await send_event("status", {"connected": False})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8550))
    print(f"\n  Claire V2.5 Dashboard → http://localhost:{port}\n")
    webbrowser.open(f"http://localhost:{port}")
    uvicorn.run("dashboard:app", host="127.0.0.1", port=port, log_level="warning")

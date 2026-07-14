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

import kokoro_tts
from google import genai
from google.genai import _common as _genai_common

_orig_convert = _genai_common.convert_to_dict

def _clean_enums(value):
    import enum as _enum
    if isinstance(value, _enum.Enum):
        return value.value
    elif isinstance(value, dict):
        return {k: _clean_enums(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_clean_enums(v) for v in value]
    return value

def _patched_convert(obj, convert_keys=False):
    res = _orig_convert(obj, convert_keys)
    return _clean_enums(res)

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
VOICES = [
    "Aoede", "Kore", "Puck", "Charon", "Fenrir",
    "Kokoro Sarah (US Female)",
    "Kokoro Bella (US Female)",
    "Kokoro Adam (US Male)",
    "Kokoro Emma (UK Female)",
    "ElevenLabs Adam (US Male)",
    "ElevenLabs Rachel (US Female)"
]
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Claire V2.5 Dashboard")
_memory = DriveMemory()
_active_session: bool = False
_last_error: str | None = None
_woop_coaching_active: bool = False
_custom_claire_energy: float | None = None


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
    global _woop_coaching_active, _custom_claire_energy
    now = datetime.now()
    daily = get_daily_context()
    reunion = format_time_since(mem_ctx.last_seen, now)
    
    # Custom Energy override
    effective_energy = _custom_claire_energy if _custom_claire_energy is not None else ego.energy
    prosody = _prosody_instruction(effective_energy)
    
    prompt_parts = [
        CLAIRE_PERSONA_OS,
        build_layer3(EgoState(energy=effective_energy, valence=ego.valence, arousal=ego.arousal)),
        build_layer5(daily, now, reunion),
        f"# WAS ICH ÜBER KEV WEISS (Memory)\n{mem_ctx.to_prompt_string()}",
        f"# PROSODIE\n{prosody}",
    ]
    
    if _woop_coaching_active:
        prompt_parts.append(
            "# SOCRATIC WOOP COACHING DIRECTIVE\n"
            "Wende das sokratische WOOP-Interventionsmodell an:\n"
            "- Führe Kev strukturiert durch Wunsch (Wish), bestes Ergebnis (Outcome) und das innere Hindernis (Obstacle).\n"
            "- Hilf ihm, einen konkreten Wenn-Dann-Plan (Plan) zu formulieren.\n"
            "- Stelle offene, reflektierende Fragen und gib keine schnellen Lösungen vor."
        )
        
    return "\n\n".join(prompt_parts)


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
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"}
    )


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


# ── ADRESSEN & SYSTEMPFADE ──────────────────────────────────────────────────
OBSIDIAN_VAULT = "/Users/kevinkuck/Library/Mobile Documents/iCloud~md~obsidian/Documents/00_KKI_Vault"
DESKTOP_MASTERAKTE = "/Users/kevinkuck/Desktop/Meister_Gem_Kontext/00 MASTERAKTE_V2_3_Full_Data.md"


# ── SIMULATION SETTINGS ──────────────────────────────────────────────────────
@app.get("/api/simulation/settings")
async def get_sim_settings():
    global _woop_coaching_active, _custom_claire_energy
    return JSONResponse({
        "woopCoaching": _woop_coaching_active,
        "claireEnergy": _custom_claire_energy if _custom_claire_energy is not None else -1
    })


@app.post("/api/simulation/settings")
async def post_sim_settings(data: dict):
    global _woop_coaching_active, _custom_claire_energy
    _woop_coaching_active = data.get("woopCoaching", False)
    val = data.get("claireEnergy", -1)
    if val < 0:
        _custom_claire_energy = None
    else:
        _custom_claire_energy = float(val)
    return JSONResponse({"status": "ok", "woopCoaching": _woop_coaching_active, "claireEnergy": val})


# ── RAG CRUD ENDPOINTS ────────────────────────────────────────────────────────
@app.get("/api/memory/list")
async def list_memory():
    facts = _memory.load_facts()
    return JSONResponse([f.to_dict() for f in facts])


@app.post("/api/memory/create")
async def create_memory(data: dict):
    cat = data.get("category", "personal_fact")
    content = data.get("content", "")
    importance = float(data.get("importance", 0.5))
    if not content.strip():
        return JSONResponse({"error": "Inhalt darf nicht leer sein"}, status_code=400)
    entry = _memory.create_fact(cat, content, importance)
    return JSONResponse({"status": "ok", "fact": entry.to_dict()})


@app.post("/api/memory/update")
async def update_memory(data: dict):
    fact_id = data.get("id")
    cat = data.get("category")
    content = data.get("content")
    importance = float(data.get("importance", 0.5))
    if fact_id is None or not content:
        return JSONResponse({"error": "Fehlende Parameter"}, status_code=400)
    _memory.update_fact(int(fact_id), cat, content, importance)
    return JSONResponse({"status": "ok"})


@app.delete("/api/memory/delete/{fact_id}")
async def delete_memory(fact_id: int):
    _memory.delete_fact(fact_id)
    return JSONResponse({"status": "ok"})


# ── OBSIDIAN ARCHIV ENDPOINTS ─────────────────────────────────────────────────
@app.get("/api/obsidian/files")
async def list_obsidian_files():
    vault = Path(OBSIDIAN_VAULT)
    if not vault.exists():
        return JSONResponse({"error": "Obsidian Vault nicht gefunden"}, status_code=404)
    
    files = []
    categories = ["00_System_Governance", "04_Dev_Systems"]
    for cat in categories:
        cat_dir = vault / cat
        if not cat_dir.exists():
            continue
        for root, _, fs in os.walk(cat_dir):
            for f in fs:
                if f.endswith(".md") and not f.startswith("."):
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(vault)
                    files.append({
                        "name": f,
                        "relative_path": str(rel_p),
                        "category": cat,
                        "size": full_p.stat().st_size
                    })
    return JSONResponse(files)


@app.get("/api/obsidian/file")
async def get_obsidian_file(path: str):
    vault = Path(OBSIDIAN_VAULT)
    file_path = vault / path
    if not str(file_path.resolve()).startswith(str(vault.resolve())):
        return JSONResponse({"error": "Ungültiger Pfad"}, status_code=403)
    if not file_path.exists():
        return JSONResponse({"error": "Datei nicht gefunden"}, status_code=404)
    
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return JSONResponse({"content": content, "path": path})


@app.post("/api/obsidian/file")
async def post_obsidian_file(data: dict):
    path = data.get("path")
    content = data.get("content")
    if not path or content is None:
        return JSONResponse({"error": "Fehlende Parameter"}, status_code=400)
        
    vault = Path(OBSIDIAN_VAULT)
    file_path = vault / path
    if not str(file_path.resolve()).startswith(str(vault.resolve())):
        return JSONResponse({"error": "Ungültiger Pfad"}, status_code=403)
        
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    # KKI-Brücke: Wenn das die Masterakte im Obsidian-Vault ist,
    # schreiben wir die Änderung automatisch auch auf den Desktop!
    if "00 MASTERAKTE_V2_3_Full_Data.md" in path or "00_MASTERAKTE_V2_3_Full_Data.md" in path:
        desktop_file = Path(DESKTOP_MASTERAKTE)
        if desktop_file.parent.exists():
            print(f"[Sync] Spiegele Obsidian-Masterakte-Update auf Desktop...")
            with open(desktop_file, "w", encoding="utf-8") as f:
                f.write(content)
                
            # SQLite RAG Wissensdatenbank direkt im Hintergrund neu befüllen
            try:
                import sqlite3
                import import_knowledge
                import_knowledge.DB_PATH = os.path.expanduser("~/.claire_memory/claire.db")
                import_knowledge.MASTERAKTE_PATH = str(desktop_file)
                conn = sqlite3.connect(import_knowledge.DB_PATH)
                conn.execute("DELETE FROM facts")
                conn.commit()
                conn.close()
                chunks = import_knowledge.extract_chunks_from_masterakte(import_knowledge.MASTERAKTE_PATH)
                adhs_chunks = import_knowledge.extract_chunks_from_adhs(import_knowledge.ADHS_PATH)
                import_knowledge.import_to_sqlite(chunks + adhs_chunks)
                print("[Sync] Wissensdatenbank nach Masterakten-Update neu indiziert.")
            except Exception as ex:
                print(f"[Sync-Error] Fehler beim automatischen RAG-Re-Indizieren: {ex}")
                
    return JSONResponse({"status": "ok"})


# ── AI CONTEXT SYNC (Gemini Extraktion & Merge) ────────────────────────────────
@app.post("/api/context/sync")
async def extract_and_sync_context(data: dict):
    raw_text = data.get("text", "")
    if not raw_text.strip():
        return JSONResponse({"error": "Text darf nicht leer sein"}, status_code=400)
        
    try:
        client = genai.Client()
        prompt = (
            "Du bist der Lead-Architekt des KKI-Systems. Analysiere die folgenden Roh-Informationen von Kevin (Kev) "
            "und extrahiere kognitive Updates.\n\n"
            "Roh-Informationen:\n"
            f"\"\"\"\n{raw_text}\n\"\"\"\n\n"
            "Deine Aufgabe:\n"
            "1. Bestimme alle neuen Fakten, die in die RAG-Wissensdatenbank eingepflegt werden sollen. "
            "Klassifiziere jeden Fakt in eine der Kategorien: personal_fact, preference, goal, relationship, past_event, emotional_state, episode. "
            "Formuliere sie als prägnante, eigenständige Sätze auf Deutsch.\n"
            "2. Extrahiere Updates für Kevs Masterakte (00 MASTERAKTE_V2_3_Full_Data.md). "
            "Welche existierenden Abschnitte (z.B. AKTIVE PROJEKTE & STATUS, TECHNISCHE KOMPETENZEN, BEZIEHUNGSLANDSCHAFT) müssen aktualisiert werden? "
            "Formuliere die konkreten Textblöcke, die hinzugefügt oder modifiziert werden sollen.\n\n"
            "Antwort MUSS ein gültiges JSON-Objekt sein mit exakt dieser Struktur:\n"
            "{\n"
            "  \"rag_facts\": [\n"
            "    {\"category\": \"personal_fact\", \"content\": \"Erklärung des Fakts...\", \"importance\": 0.7}\n"
            "  ],\n"
            "  \"masterakte_updates\": [\n"
            "    {\n"
            "      \"section\": \"AKTIVE PROJEKTE & STATUS\",\n"
            "      \"action\": \"append|replace\",\n"
            "      \"description\": \"Kurze Beschreibung der Änderung (z.B. Ergänzung von Traktor S4 MK3 Modding)\",\n"
            "      \"new_text\": \"Der konkrete Markdown-Inhalt, der eingefügt werden soll\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        
        result = json.loads(response.text)
        
        rag_added = []
        for fact in result.get("rag_facts", []):
            cat = fact.get("category", "personal_fact")
            content = fact.get("content", "")
            importance = float(fact.get("importance", 0.5))
            if content.strip():
                msg = _memory.upsert_fact(cat, content, importance)
                rag_added.append({"category": cat, "content": content, "status": msg})
                
        desktop_file = Path(DESKTOP_MASTERAKTE)
        masterakte_merged = False
        masterakte_content = ""
        
        if desktop_file.exists():
            with open(desktop_file, "r", encoding="utf-8") as f:
                masterakte_content = f.read()
                
            updates_str = json.dumps(result.get("masterakte_updates", []), ensure_ascii=False)
            merge_prompt = (
                "Du bist ein präziser Markdown-Synthesizer. Du erhältst die aktuelle KKI-Masterakte und eine Liste von "
                "strukturierten Updates. Deine Aufgabe ist es, diese Updates nahtlos und fehlerfrei in das Dokument einzupflegen.\n\n"
                "Regeln:\n"
                "- Bewahre die exakte Struktur, YAML-Frontmatter und alle existierenden Zeilen und Linter-Formate (Leerzeilen vor/nach Überschriften, Tabellen-Abstände etc.).\n"
                "- Füge neue Einträge am Ende der jeweiligen Abschnitte an oder bearbeite existierende Einträge entsprechend der Updates.\n"
                "- Gib das VOLLSTÄNDIGE, aktualisierte Markdown-Dokument zurück. Keine Kommentare, keine Erklärungen.\n\n"
                f"Updates:\n{updates_str}\n\n"
                f"Masterakte:\n\"\"\"\n{masterakte_content}\n\"\"\""
            )
            
            merge_response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=merge_prompt
            )
            
            new_masterakte_content = merge_response.text.strip()
            if "title:" in new_masterakte_content and "GEM — MASTERAKTE" in new_masterakte_content:
                with open(desktop_file, "w", encoding="utf-8") as f:
                    f.write(new_masterakte_content)
                obsidian_file = Path(OBSIDIAN_VAULT) / "00_System_Governance" / "Masterakte" / "00_MASTERAKTE_V2_3_Full_Data.md"
                if obsidian_file.parent.exists():
                    with open(obsidian_file, "w", encoding="utf-8") as f:
                        f.write(new_masterakte_content)
                
                try:
                    import sqlite3
                    import import_knowledge
                    import_knowledge.DB_PATH = os.path.expanduser("~/.claire_memory" / "claire.db")
                    import_knowledge.MASTERAKTE_PATH = str(desktop_file)
                    
                    conn = sqlite3.connect(import_knowledge.DB_PATH)
                    conn.execute("DELETE FROM facts")
                    conn.commit()
                    conn.close()
                    
                    chunks = import_knowledge.extract_chunks_from_masterakte(import_knowledge.MASTERAKTE_PATH)
                    adhs_chunks = import_knowledge.extract_chunks_from_adhs(import_knowledge.ADHS_PATH)
                    import_knowledge.import_to_sqlite(chunks + adhs_chunks)
                except Exception as ex:
                    print(f"[Sync-Error] RAG-Update fehlgeschlagen: {ex}")
                    
                masterakte_merged = True
                
        return JSONResponse({
            "status": "ok",
            "rag_facts": rag_added,
            "masterakte_merged": masterakte_merged,
            "raw_extraction": result
        })
        
    except Exception as e:
        print(f"[AI-Sync-Error] Fehler im Sync-Center: {e}")
        return JSONResponse({"error": f"KI-Extraktion fehlgeschlagen: {str(e)}"}, status_code=500)


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
    if _custom_claire_energy is not None:
        blended_e = _custom_claire_energy
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

    # Check if custom TTS is requested (Kokoro or ElevenLabs) and handle fallbacks
    use_custom_tts = False
    if voice.startswith("Kokoro"):
        if not kokoro_tts.is_available():
            await send_event("error", {
                "msg": "Lokales Kokoro-TTS ist auf diesem System nicht installiert. Verwende automatischen Fallback auf Gemini Neural Voice (Aoede)."
            })
            voice = "Aoede"
        else:
            use_custom_tts = True
    elif voice.startswith("ElevenLabs"):
        if not os.getenv("ELEVENLABS_API_KEY"):
            await send_event("error", {
                "msg": "ELEVENLABS_API_KEY fehlt im Environment. Verwende automatischen Fallback auf Gemini Neural Voice (Aoede)."
            })
            voice = "Aoede"
        else:
            use_custom_tts = True

    client = genai.Client()

    if use_custom_tts:
        # Request TEXT from Gemini, so we can generate audio locally via Kokoro/ElevenLabs
        config = genai.types.LiveConnectConfig(
            response_modalities=["TEXT"],
            system_instruction=system_prompt,
            output_audio_transcription=genai.types.AudioTranscriptionConfig(),
            input_audio_transcription=genai.types.AudioTranscriptionConfig(),
            tools=TOOLS,
        )
    else:
        # Standard Gemini Native Audio Config
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
        current_sentence = []
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
                        # Standard Gemini Audio Modality
                        if part.inline_data and isinstance(part.inline_data.data, bytes):
                            chunk = base64.b64encode(part.inline_data.data).decode()
                            await send_event("audio", {"data": chunk})
                        # Text Modality (Kokoro TTS)
                        elif part.text:
                            text_chunk = part.text
                            # Sende Live-Text an das Transkript-Panel
                            await send_event("transcript", {"role": "claire", "text": text_chunk})
                            current_sentence.append(text_chunk)
                            
                            # Wenn wir Satzzeichen finden, generieren wir Audio für den Satz
                            if any(p in text_chunk for p in [".", "!", "?", "\n"]):
                                sentence = "".join(current_sentence).strip()
                                if sentence:
                                    try:
                                        pcm_data = await kokoro_tts.generate_speech(sentence, voice)
                                        if pcm_data:
                                            chunk = base64.b64encode(pcm_data).decode()
                                            await send_event("audio", {"data": chunk})
                                    except Exception as e:
                                        logger.error(f"Kokoro synthesis failed: {e}")
                                current_sentence = []

                if sc.output_transcription:
                    t = sc.output_transcription.text
                    history.append({"role": "Claire", "content": t})
                    turn_count += 1
                    if not use_custom_tts:
                        await send_event("transcript", {"role": "claire", "text": t})
                    await send_event("session", {
                        "turns": turn_count,
                        "elapsed": int(time.time() - session_start),
                    })

                # Wenn der Turn abgeschlossen ist und noch Text im Buffer war
                if sc.turn_complete and use_custom_tts:
                    sentence = "".join(current_sentence).strip()
                    if sentence:
                        try:
                            pcm_data = await kokoro_tts.generate_speech(sentence, voice)
                            if pcm_data:
                                chunk = base64.b64encode(pcm_data).decode()
                                await send_event("audio", {"data": chunk})
                        except Exception as e:
                            logger.error(f"Custom synthesis failed: {e}")
                    current_sentence = []
                    # Session Turn Count verwalten
                    history.append({"role": "Claire", "content": sentence})
                    turn_count += 1
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

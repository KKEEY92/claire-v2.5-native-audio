import os
import logging
import asyncio
import json
import urllib.request
import urllib.error

logger = logging.getLogger("claire.tts")

# Versuche Kokoro zu laden
HAS_KOKORO = False
_pipeline = None

try:
    from kokoro import KPipeline
    HAS_KOKORO = True
    logger.info("Kokoro Python library (hexgrad) detected.")
except ImportError:
    try:
        from kokoro_onnx import Kokoro
        HAS_KOKORO = True
        logger.info("Kokoro ONNX library detected.")
    except ImportError:
        logger.info("Kokoro is not installed locally.")

# ElevenLabs voice mappings (Standard IDs)
ELEVENLABS_VOICES = {
    "adam": "pNInz6obpgq5paqqJJAx",
    "rachel": "21m00Tcm4TlvDq8ikWAM",
    "antoni": "ErXwobaYiN019PkySvjV",
    "bella": "EXAVITQu4vr4xnSDxMaL",
    "sarah": "EXAVITQu4vr4xnSDxMaL", # Fallback
}

def is_available() -> bool:
    """Gibt True zurück, wenn Kokoro lokal ODER ElevenLabs via API-Key verfügbar ist."""
    return HAS_KOKORO or bool(os.getenv("ELEVENLABS_API_KEY"))

async def generate_speech(text: str, voice_name: str) -> bytes:
    """
    Generiert PCM-Audio (24kHz) aus Text. Weicht je nach Stimme auf lokales
    Kokoro-TTS oder ElevenLabs-Cloud-TTS (PCM 24kHz) aus.
    """
    if voice_name.lower().startswith("elevenlabs"):
        return await _generate_elevenlabs(text, voice_name)
    
    if not HAS_KOKORO:
        raise RuntimeError("Kokoro is not installed on this system.")
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _generate_blocking, text, voice_name)

async def _generate_elevenlabs(text: str, voice_name: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set in environment.")
        
    # Voice ID ermitteln
    voice_key = "adam"
    for k in ELEVENLABS_VOICES.keys():
        if k in voice_name.lower():
            voice_key = k
            break
    voice_id = ELEVENLABS_VOICES[voice_key]
    
    # URL und Payload aufbauen
    # output_format=pcm_24000 liefert rohes 16-bit Mono-PCM mit 24kHz zurück!
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=pcm_24000"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    logger.info(f"Rufen ElevenLabs Cloud TTS auf ({voice_key})...")
    
    def _post():
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                return response.read()
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"ElevenLabs API Error: {e.code} - {err_body}")
            raise RuntimeError(f"ElevenLabs API Error: {err_body}")
            
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _post)

def _generate_blocking(text: str, voice_name: str) -> bytes:
    global _pipeline
    
    voice_key = "af_sarah"
    if "bella" in voice_name.lower():
        voice_key = "af_bella"
    elif "adam" in voice_name.lower():
        voice_key = "am_adam"
    elif "emma" in voice_name.lower():
        voice_key = "bf_emma"
    
    try:
        if _pipeline is None:
            logger.info("Initializing Kokoro KPipeline...")
            _pipeline = KPipeline(lang_code='a')
            
        generator = _pipeline(text, voice=voice_key, speed=1.0, split_pattern=r'\n+')
        all_audio = []
        import numpy as np
        
        for gs, ps, audio in generator:
            if audio is not None:
                pcm = (audio * 32767).astype(np.int16)
                all_audio.append(pcm.tobytes())
                
        return b"".join(all_audio)
        
    except Exception as e:
        logger.error(f"Error during local Kokoro synthesis: {e}")
        raise e

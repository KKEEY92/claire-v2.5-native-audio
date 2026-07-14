"""
launcher.py — Claire V2.5 Native Audio Entry Point.

Single start: Port-Check → Device-Scan → Probes → Dashboard.
Doppelklick via ~/Desktop/Claire V2.5.command
"""
import os
import socket
import subprocess
import sys
import webbrowser

from dotenv import load_dotenv
load_dotenv()

PORT = 8550


def check_port(port: int):
    """Prüft ob Port frei ist. Bei Blockade: PID anzeigen, abbrechen."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", port)) != 0:
            return
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            capture_output=True, text=True, timeout=3,
        )
        pid = result.stdout.strip()
    except Exception:
        pid = "?"
    print(f"\n  ✖  Port {port} ist belegt (PID: {pid})")
    print(f"     Beende den Prozess: kill {pid}")
    print(f"     Oder: lsof -ti :{port} | xargs kill\n")
    sys.exit(1)


def check_claire_mix():
    """Scannt PyAudio-Devices nach Claire_Mix / SoundSyphon / BlackHole."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        targets = ["claire_mix", "soundsyphon", "blackhole"]
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            name = info.get("name", "").lower()
            if any(t in name for t in targets) and info.get("maxInputChannels", 0) > 0:
                os.environ["CLAIRE_INPUT_DEVICE"] = str(i)
                print(f"  ✓  Audio-Device: {info['name']} (Index {i})")
                pa.terminate()
                return
        pa.terminate()
        print("  ⚠  Kein Claire_Mix/SoundSyphon/BlackHole gefunden — Browser-Mic wird genutzt")
    except ImportError:
        print("  ⚠  PyAudio nicht installiert — Browser-Mic wird genutzt")


def probe_gemini() -> bool:
    """Prüft ob Gemini API erreichbar ist."""
    import urllib.request
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("  ✖  GOOGLE_API_KEY nicht gesetzt")
        return False
    try:
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
            method="GET",
        )
        urllib.request.urlopen(req, timeout=3)
        print("  ✓  Gemini API erreichbar")
        return True
    except Exception as e:
        print(f"  ⚠  Gemini API nicht erreichbar: {e}")
        return False


def probe_lm_studio() -> bool:
    """Prüft ob LM Studio auf localhost:1234 läuft."""
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:1234/v1/models", timeout=2)
        print("  ✓  LM Studio erreichbar (Airgap-Fallback verfügbar)")
        return True
    except Exception:
        print("  –  LM Studio nicht erreichbar")
        return False


def main():
    model = os.getenv("CLAIRE_MODEL", "gemini-2.5-flash-native-audio-latest")
    voice = os.getenv("CLAIRE_VOICE", "Aoede")

    print(f"""
╔══════════════════════════════════════════════════════════╗
║  Claire V2.5 — Native Audio Launcher                    ║
║  Modell:  {model:<47s}║
║  Stimme:  {voice:<47s}║
║  Port:    {PORT:<47d}║
╚══════════════════════════════════════════════════════════╝
""")

    print("  Preflight-Checks:\n")
    check_port(PORT)

    gemini_ok = probe_gemini()
    lm_studio_ok = probe_lm_studio()
    check_claire_mix()

    os.environ["CLAIRE_GEMINI_REACHABLE"] = "1" if gemini_ok else "0"
    os.environ["CLAIRE_LMSTUDIO_REACHABLE"] = "1" if lm_studio_ok else "0"
    os.environ["CLAIRE_AIRGAP_READY"] = "1" if (lm_studio_ok and not gemini_ok) else "0"

    if not gemini_ok and not lm_studio_ok:
        print("\n  ⚠  Weder Gemini noch LM Studio erreichbar — Dashboard startet trotzdem\n")

    print(f"\n  → Dashboard: http://localhost:{PORT}\n")
    webbrowser.open(f"http://localhost:{PORT}")

    import uvicorn
    uvicorn.run("dashboard:app", host="0.0.0.0", port=PORT, log_level="warning")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Claire V2.5 beendet.")

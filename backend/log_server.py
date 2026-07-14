"""
log_server.py – Host-seitiger Live-Log-Stream für Claires Container.

Läuft auf dem Mac-HOST (nicht im Container — nur der Host hat die Docker-CLI) und
streamt das echte `docker compose logs -f agent` per Server-Sent-Events (SSE) an
das Frontend (LIVE-Tab → "Raw stdout"). Das ist das forensische Terminal-Protokoll.

Start:   .venv/bin/python log_server.py
Quelle:  LOG_SOURCE=docker (Default) → docker compose logs -f --tail=200 agent
         LOG_SOURCE=file           → tail -f $LOG_FILE (lokaler Mac-Modus)
Port:    LOG_SERVER_PORT (Default 3002)  ·  Vite proxyt /logs → localhost:3002
"""
import os
import subprocess
import shutil

from flask import Flask, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Worktree-Verzeichnis (wo docker-compose.yml liegt) = Verzeichnis dieser Datei.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.getenv("LOG_SERVER_PORT", "3002"))
SOURCE = os.getenv("LOG_SOURCE", "docker").lower()
LOG_FILE = os.getenv("LOG_FILE", "/tmp/claire_local.log")
SERVICE = os.getenv("LOG_SERVICE", "agent")


def _docker_cmd() -> list[str]:
    """docker compose (v2) bevorzugt, Fallback docker-compose (v1)."""
    docker = shutil.which("docker") or "docker"
    return [docker, "compose", "logs", "-f", "--tail=200", "--no-color", SERVICE]


def _stream():
    """Generator: liest stdout des Log-Prozesses zeilenweise und gibt SSE-Frames aus."""
    if SOURCE == "file":
        cmd = ["tail", "-n", "200", "-F", LOG_FILE]
        cwd = None
    else:
        cmd = _docker_cmd()
        cwd = PROJECT_DIR

    yield f"event: hello\ndata: log-stream verbunden ({SOURCE}: {' '.join(cmd)})\n\n"
    try:
        proc = subprocess.Popen(
            cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )
    except Exception as e:
        yield f"data: [log_server] Konnte Quelle nicht starten: {e}\n\n"
        return

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip("\n")
            # SSE: jede Zeile als eigenes data-Frame (mehrzeilig-sicher)
            yield "data: " + line.replace("\r", "") + "\n\n"
    except GeneratorExit:
        # Client hat die Verbindung getrennt → Log-Prozess beenden
        proc.terminate()
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


@app.get("/logs")
def logs():
    return Response(
        _stream(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/health")
def health():
    return {"service": "claire-log-server", "status": "ok", "source": SOURCE}


if __name__ == "__main__":
    print(f"[log_server] SSE auf :{PORT}  (Quelle: {SOURCE}, Service: {SERVICE})", flush=True)
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)

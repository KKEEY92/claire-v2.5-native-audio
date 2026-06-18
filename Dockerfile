# Claire V2 – Agent + Token-Server (Linux / Python 3.12)
# Entkoppelt den Agenten von macOS 27 Beta + Python 3.15.0a1:
#   • stabiler multiprocessing-IPC (PROCESS-Executor) — kein 60s-"unresponsive"-Kill
#   • onnxruntime verfügbar → Silero VAD (echte Turn-Detection)
# LM Studio (Mac-GPU) und der Browser bleiben nativ auf dem Host.
FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Audio-/TLS-Systembibliotheken für die Voice-Pipeline
RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies zuerst (Docker-Layer-Cache)
COPY requirements.txt requirements-docker.txt ./
RUN pip install --upgrade pip && pip install -r requirements-docker.txt

# Anwendungscode
COPY agent.py persona.py memory.py token_server.py agent_telemetry.py ./

# Silero-/Plugin-Modelldateien vorab ins Image cachen (beschleunigt ersten Job).
# Best-effort: bricht den Build bei Netzwerk-Hickups nicht ab.
RUN python agent.py download-files || true

# Default: Voice-Agent im Prod-Modus (docker-compose überschreibt je Service)
CMD ["python", "agent.py", "start"]

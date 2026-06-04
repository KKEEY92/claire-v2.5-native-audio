"""
token_server.py — Lokaler LiveKit JWT-Token-Server für Claire V2.

Läuft auf http://localhost:3001
Endpoint: GET /token?room=claire&identity=user-123

Start:
    python token_server.py

Abhängigkeiten (einmalig):
    pip install livekit-api flask flask-cors python-dotenv
"""
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from livekit.api import AccessToken, VideoGrants

load_dotenv()

API_KEY    = os.getenv("LIVEKIT_API_KEY")
API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not API_KEY or not API_SECRET:
    raise RuntimeError(
        "[Token-Server] LIVEKIT_API_KEY oder LIVEKIT_API_SECRET fehlen in .env!"
    )

app = Flask(__name__)
CORS(app, origins=["http://localhost:5173", "http://127.0.0.1:5173"])


@app.get("/token")
def get_token():
    room     = request.args.get("room", "claire")
    identity = request.args.get("identity", "user-anon")

    token = (
        AccessToken(API_KEY, API_SECRET)
        .with_identity(identity)
        .with_name(identity)
        .with_grants(VideoGrants(
            room_join=True,
            room=room,
            can_publish=True,
            can_subscribe=True,
        ))
        .to_jwt()
    )

    print(f"[Token-Server] Token ausgestellt → room={room} identity={identity}")
    return jsonify({"token": token})


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "claire-token-server"})


if __name__ == "__main__":
    print("[Token-Server] Gestartet auf http://localhost:3001/token")
    print(f"[Token-Server] API_KEY: {API_KEY[:8]}...")
    app.run(host="0.0.0.0", port=3001, debug=False)

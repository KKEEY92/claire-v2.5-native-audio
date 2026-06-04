---
description: # WORKSPACE WORKFLOW: CLAIRE V2 PIPELINE
---

# WORKSPACE WORKFLOW: CLAIRE V2 PIPELINE
Gehe strikt chronologisch vor.

## SCHRITT 1: DER ISOLIERTE KERN (`brain_test.py`)
- Baue die reine Logik (EmotionEngine, Tool Calling, Drive API RAG) ohne Audio.
- Ziel: Textbasiertes Terminal-Skript zur Verifizierung.

## SCHRITT 2: BACKEND & LIVEKIT WRAPPER (`agent.py`)
- Importiere den Kern, wickle die LiveKit `VoicePipelineAgent` Architektur darum.
- Integriere VAD, TTS und STT für minimale Latenz.

## SCHRITT 3: FRONTEND INTEGRATION (STITCH & VERTEX)
- Baue das Frontend-Interface basierend auf der Stitch API.
- Wende striktes Google Vertex Design an (High-End Enterprise Look, Analytics-Dashboards für Claires Energie-Level, sauberes State-Management).

## SCHRITT 4: DOKUMENTATION & DEPLOYMENT (europe-west3)
- Finalisiere die professionelle `README.md` mit der gesamten Architektur-Doku.
- Führe den GitHub-Sync durch.
- Deployment-Befehl ausgeben: `gcloud run deploy realtime-agent --source . --region europe-west3 --allow-unauthenticated`.

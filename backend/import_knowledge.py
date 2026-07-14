import os
import sys
import sqlite3
import datetime
import struct
import json
import re

# Füge Pfad für Imports hinzu
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from memory import _compute_embedding, _pack_embedding, CATEGORIES

DB_PATH = os.path.expanduser("~/.claire_memory/claire.db")
MASTERAKTE_PATH = "/Users/kevinkuck/Desktop/Meister_Gem_Kontext/00 MASTERAKTE_V2_3_Full_Data.md"
ADHS_PATH = "/Users/kevinkuck/01_VIBE_Code_AGENTIC_AI_KEV/00_PROJECTE_MAIN/01_Active_Workspace/kki-frameworks/Perplexity_Projektanweisung_ADHS_Staerken.md"

def extract_chunks_from_masterakte(filepath: str) -> list[dict]:
    if not os.path.exists(filepath):
        print(f"Masterakte file not found at {filepath}")
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    chunks = []
    # 1. Extrahiere Schlüssel-Abschnitte anhand von Überschriften
    # Wir teilen nach H2 (##) und H3 (###) auf
    sections = re.split(r'\n##\s+', content)
    
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
            
        lines = sec.split("\n")
        title = lines[0].strip().replace("**", "").replace("*", "")
        body = "\n".join(lines[1:]).strip()
        
        if not body:
            continue
            
        # Bestimme Kategorie anhand des Titels
        category = "personal_fact"
        importance = 0.5
        tags = []
        
        title_lower = title.lower()
        if "profil" in title_lower or "identität" in title_lower:
            category = "personal_fact"
            importance = 0.8
            tags = ["identity", "profile"]
        elif "neuro" in title_lower or "adhs" in title_lower or "human design" in title_lower:
            category = "emotional_state"
            importance = 0.9
            tags = ["neurodivergence", "adhs", "profile"]
        elif "berufliche" in title_lower or "chronologie" in title_lower:
            category = "past_event"
            importance = 0.7
            tags = ["career", "history"]
        elif "jobits" in title_lower:
            category = "past_event"
            importance = 0.8
            tags = ["jobits", "termination", "history"]
        elif "zertifikate" in title_lower or "qualifikationen" in title_lower:
            category = "preference"
            importance = 0.6
            tags = ["skills", "certificates"]
            
        # Unterteilen in kleinere Abschnitte falls sehr lang
        if len(body) > 1200:
            subsections = re.split(r'\n###\s+', body)
            for sub in subsections:
                sub = sub.strip()
                if not sub:
                    continue
                sub_lines = sub.split("\n")
                sub_title = sub_lines[0].strip().replace("**", "").replace("*", "")
                sub_body = "\n".join(sub_lines[1:]).strip()
                if sub_body:
                    chunks.append({
                        "category": category,
                        "content": f"{title} - {sub_title}:\n{sub_body}",
                        "importance": importance,
                        "tags": tags + [sub_title.lower()]
                    })
        else:
            chunks.append({
                "category": category,
                "content": f"{title}:\n{body}",
                "importance": importance,
                "tags": tags
            })
            
    return chunks

def extract_chunks_from_adhs(filepath: str) -> list[dict]:
    if not os.path.exists(filepath):
        print(f"ADHS Strengths file not found at {filepath}")
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
        
    chunks = []
    sections = re.split(r'\n##\s+', content)
    
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
            
        lines = sec.split("\n")
        title = lines[0].strip().replace("**", "").replace("*", "")
        body = "\n".join(lines[1:]).strip()
        
        if not body:
            continue
            
        chunks.append({
            "category": "preference",
            "content": f"ADHS Spezialist Leitlinie - {title}:\n{body}",
            "importance": 0.85,
            "tags": ["adhs", "neurodivergence", "strategy", "methodology"]
        })
        
    return chunks

def import_to_sqlite(chunks: list[dict]):
    print(f"Verbinde mit SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # KKI Clean Start: Alte Fakten vor Neu-Import löschen
    print("Leere alte facts Tabelle für v2.3.0...")
    cursor.execute("DELETE FROM facts")
    
    imported_count = 0
    skipped_count = 0
    
    for c in chunks:
        content = c["content"]
        category = c["category"]
        importance = c["importance"]
        tags_str = json.dumps(c["tags"])
        timestamp = datetime.datetime.now().isoformat()
        
        # Duplikatschutz
        cursor.execute("SELECT id FROM facts WHERE content = ?", (content,))
        if cursor.fetchone():
            skipped_count += 1
            continue
            
        # Berechne Embedding (Vertex AI)
        print(f"Berechne Embedding für Chunk ({len(content)} Zeichen)...")
        emb = _compute_embedding(content)
        emb_blob = _pack_embedding(emb)
        
        cursor.execute(
            """
            INSERT INTO facts (category, content, timestamp, importance, tags, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (category, content, timestamp, importance, tags_str, emb_blob)
        )
        imported_count += 1
        
    conn.commit()
    conn.close()
    print(f"\n✓ Import abgeschlossen!")
    print(f" - Neu importiert: {imported_count} Fakten")
    print(f" - Übersprungen (bereits vorhanden): {skipped_count} Fakten")

if __name__ == "__main__":
    print("=== CLAIRE KNOWLEDGE BASE IMPORT ===")
    
    chunks = []
    chunks += extract_chunks_from_masterakte(MASTERAKTE_PATH)
    chunks += extract_chunks_from_adhs(ADHS_PATH)
    
    print(f"Gefundene Wissens-Chunks: {len(chunks)}")
    
    if chunks:
        import_to_sqlite(chunks)
    else:
        print("Keine Wissens-Chunks zum Importieren gefunden.")

"""
memory.py – Persistente Memory für Claire (SQLite-Primary, Drive-Backup).

Architektur Memory 3.0:
  • SQLite unter ~/.claire_memory/claire.db als Primary Store (WAL-Mode)
  • Google Drive als optionaler async Backup (best-effort)
  • 7 Kategorien, Duplikatschutz (>60% Wort-Überschneidung)
  • Embedding-Retrieval via Vertex AI text-multilingual-embedding-002
  • Fallback: Keyword-Matching für Facts ohne Embedding
"""
import json
import math
import os
import sqlite3
import struct
import threading
import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import google.auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
    _DRIVE_OK = True
except ImportError:
    _DRIVE_OK = False

try:
    import vertexai
    from vertexai.language_models import TextEmbeddingModel
    _EMBEDDING_OK = True
except ImportError:
    _EMBEDDING_OK = False

_EMBEDDING_MODEL_NAME = "text-multilingual-embedding-002"
_embedding_model: Optional["TextEmbeddingModel"] = None

_DB_DIR = Path.home() / ".claire_memory"
_DB_PATH = _DB_DIR / "claire.db"


# ── SCHEMA ────────────────────────────────────────────────────────────────────

CATEGORIES = [
    "personal_fact",
    "emotional_state",
    "relationship",
    "past_event",
    "preference",
    "goal",
    "episode",
]


@dataclass
class MemoryEntry:
    id: Optional[int] = None
    category: str = "personal_fact"
    content: str = ""
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)
    embedding: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id":         self.id,
            "category":   self.category,
            "content":    self.content,
            "timestamp":  self.timestamp,
            "importance": self.importance,
            "tags":       self.tags,
            "embedding":  self.embedding,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(
            id=d.get("id"),
            category=d.get("category", "personal_fact"),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", datetime.datetime.now().isoformat()),
            importance=float(d.get("importance", 0.5)),
            tags=d.get("tags", []),
            embedding=d.get("embedding", []),
        )


# ── EMBEDDING HELPERS ─────────────────────────────────────────────────────────

def _get_embedding_model() -> Optional["TextEmbeddingModel"]:
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    if not _EMBEDDING_OK:
        return None
    try:
        project = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west3")
        if project:
            vertexai.init(project=project, location=location)
        _embedding_model = TextEmbeddingModel.from_pretrained(_EMBEDDING_MODEL_NAME)
        print(f"[Memory] Embedding-Modell geladen: {_EMBEDDING_MODEL_NAME}")
        return _embedding_model
    except Exception as e:
        print(f"[Memory] Embedding-Modell nicht verfügbar: {e}")
        return None


def _compute_embedding(text: str) -> list[float]:
    model = _get_embedding_model()
    if model is None:
        return []
    try:
        result = model.get_embeddings([text])
        return result[0].values
    except Exception as e:
        print(f"[Memory] Embedding-Fehler: {e}")
        return []


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot    = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _keyword_score(query: str, content: str) -> float:
    q_words = set(query.lower().split())
    c_words = set(content.lower().split())
    if not q_words:
        return 0.0
    matches = len(q_words & c_words)
    return matches / len(q_words)


@dataclass
class MemoryContext:
    facts: list[MemoryEntry] = field(default_factory=list)
    ego_energy: float = 0.65
    last_summary: str = ""
    last_seen: str = ""

    def to_prompt_string(self, max_per_cat: int = 5) -> str:
        if not self.facts and not self.last_summary:
            return "Noch keine gespeicherten Informationen über Kev."

        by_cat: dict[str, list[MemoryEntry]] = {}
        for e in self.facts:
            by_cat.setdefault(e.category, []).append(e)

        lines: list[str] = []
        for cat, entries in by_cat.items():
            sorted_e = sorted(entries, key=lambda x: x.timestamp, reverse=True)
            lines.append(f"[{cat}]")
            for e in sorted_e[:max_per_cat]:
                lines.append(f"  • {e.content}")

        if self.last_summary:
            lines += ["\n[Letztes Gespräch]", f"  {self.last_summary}"]

        return "\n".join(lines)


# ── DUPLIKATSCHUTZ ────────────────────────────────────────────────────────────

def _word_overlap(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


# ── SQLITE HELPERS ────────────────────────────────────────────────────────────

def _pack_embedding(vec: list[float]) -> bytes:
    if not vec:
        return b""
    return struct.pack(f"{len(vec)}f", *vec)


def _unpack_embedding(blob: bytes) -> list[float]:
    if not blob:
        return []
    count = len(blob) // 4
    return list(struct.unpack(f"{count}f", blob))


def _init_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            importance REAL DEFAULT 0.5,
            tags TEXT DEFAULT '[]',
            embedding BLOB DEFAULT x''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ego_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            energy REAL NOT NULL,
            ts TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            ts TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transcripts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            ts TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            duration INTEGER DEFAULT 0,
            turns INTEGER DEFAULT 0,
            memory_saves INTEGER DEFAULT 0,
            energy REAL DEFAULT 0.65
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation TEXT NOT NULL,
            path TEXT NOT NULL,
            payload TEXT NOT NULL,
            created_at TEXT NOT NULL,
            synced INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn


# ── DRIVE MEMORY (SQLite-Primary) ────────────────────────────────────────────

class DriveMemory:
    """
    SQLite-primary Memory mit optionalem Google Drive Backup.

    Primary: ~/.claire_memory/claire.db (WAL-Mode, sofortige Persistenz)
    Backup:  Google Drive (async, best-effort via sync_queue)
    """

    _SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        self._folder_id = os.getenv("GDRIVE_MEMORY_FOLDER_ID")
        self._svc = None
        self._facts_cache: Optional[list[MemoryEntry]] = None
        self._lock = threading.Lock()

        # SQLite init
        self._db = _init_db(_DB_PATH)
        print(f"[Memory] SQLite verbunden: {_DB_PATH}")

        # Drive init (optional backup)
        if _DRIVE_OK and self._folder_id:
            try:
                creds, _ = google.auth.default(scopes=self._SCOPES)
                self._svc = build("drive", "v3", credentials=creds)
                print("[Memory] Google Drive als Backup verbunden ✓  (ADC)")
                self._initial_sync()
            except Exception as e:
                print(f"[Memory] Drive-Backup nicht verfügbar ({e}) — SQLite-only")
        else:
            print("[Memory] SQLite-only Modus (kein Drive-Backup)")

        # Background sync thread
        if self._svc:
            t = threading.Thread(target=self._process_sync_queue, daemon=True)
            t.start()

    def _initial_sync(self):
        """Pull from Drive into SQLite if SQLite is empty and Drive has data."""
        with self._lock:
            row = self._db.execute("SELECT COUNT(*) FROM facts").fetchone()
            if row[0] > 0:
                return

        raw = self._drive_read_json("facts.json")
        if not isinstance(raw, list) or not raw:
            return

        entries = [MemoryEntry.from_dict(e) for e in raw if "content" in e]
        if not entries:
            return

        print(f"[Memory] Initial-Sync: {len(entries)} Facts von Drive → SQLite")
        with self._lock:
            for e in entries:
                self._db.execute(
                    "INSERT INTO facts (category, content, timestamp, importance, tags, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                    (e.category, e.content, e.timestamp, e.importance, json.dumps(e.tags), _pack_embedding(e.embedding)),
                )
            self._db.commit()

        ego_raw = self._drive_read_json("ego_state.json")
        if isinstance(ego_raw, dict) and "energy" in ego_raw:
            with self._lock:
                self._db.execute(
                    "INSERT OR REPLACE INTO ego_state (id, energy, ts) VALUES (1, ?, ?)",
                    (ego_raw["energy"], ego_raw.get("ts", datetime.datetime.now().isoformat())),
                )
                self._db.commit()

        summary_raw = self._drive_read_json("last_summary.json")
        if isinstance(summary_raw, dict) and summary_raw.get("text"):
            with self._lock:
                self._db.execute(
                    "INSERT INTO summaries (text, ts) VALUES (?, ?)",
                    (summary_raw["text"], summary_raw.get("ts", datetime.datetime.now().isoformat())),
                )
                self._db.commit()

    # ── PUBLIC API (identische Signaturen) ────────────────────────────────────

    def load_facts(self) -> list[MemoryEntry]:
        if self._facts_cache is not None:
            return self._facts_cache
        with self._lock:
            rows = self._db.execute(
                "SELECT id, category, content, timestamp, importance, tags, embedding FROM facts"
            ).fetchall()
        self._facts_cache = [
            MemoryEntry(
                id=r[0], category=r[1], content=r[2], timestamp=r[3],
                importance=r[4], tags=json.loads(r[5]),
                embedding=_unpack_embedding(r[6]),
            )
            for r in rows
        ]
        return self._facts_cache

    def save_facts(self, entries: list[MemoryEntry]):
        with self._lock:
            self._db.execute("DELETE FROM facts")
            for e in entries:
                cursor = self._db.execute(
                    "INSERT INTO facts (id, category, content, timestamp, importance, tags, embedding) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (e.id, e.category, e.content, e.timestamp, e.importance, json.dumps(e.tags), _pack_embedding(e.embedding)),
                )
                if e.id is None:
                    e.id = cursor.lastrowid
            self._db.commit()
        self._facts_cache = entries
        self._queue_drive_sync("facts.json", json.dumps([e.to_dict() for e in entries], ensure_ascii=False))

    def create_fact(self, category: str, content: str, importance: float = 0.5) -> MemoryEntry:
        if category not in CATEGORIES:
            category = "personal_fact"
        embedding = _compute_embedding(content)
        entry = MemoryEntry(
            category=category,
            content=content,
            importance=importance,
            embedding=embedding
        )
        with self._lock:
            cursor = self._db.execute(
                "INSERT INTO facts (category, content, timestamp, importance, tags, embedding) VALUES (?, ?, ?, ?, ?, ?)",
                (entry.category, entry.content, entry.timestamp, entry.importance, json.dumps(entry.tags), _pack_embedding(entry.embedding))
            )
            entry.id = cursor.lastrowid
            self._db.commit()
        
        # Cache zurücksetzen, damit neu geladen wird
        self._facts_cache = None
        self.load_facts()
        self._queue_drive_sync("facts.json", json.dumps([e.to_dict() for e in self.load_facts()], ensure_ascii=False))
        return entry

    def update_fact(self, fact_id: int, category: str, content: str, importance: float = 0.5) -> bool:
        if category not in CATEGORIES:
            category = "personal_fact"
        embedding = _compute_embedding(content)
        ts = datetime.datetime.now().isoformat()
        with self._lock:
            self._db.execute(
                "UPDATE facts SET category = ?, content = ?, timestamp = ?, importance = ?, embedding = ? WHERE id = ?",
                (category, content, ts, importance, _pack_embedding(embedding), fact_id)
            )
            self._db.commit()
        
        self._facts_cache = None
        self.load_facts()
        self._queue_drive_sync("facts.json", json.dumps([e.to_dict() for e in self.load_facts()], ensure_ascii=False))
        return True

    def delete_fact(self, fact_id: int) -> bool:
        with self._lock:
            self._db.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
            self._db.commit()
        
        self._facts_cache = None
        self.load_facts()
        self._queue_drive_sync("facts.json", json.dumps([e.to_dict() for e in self.load_facts()], ensure_ascii=False))
        return True

    def upsert_fact(self, category: str, content: str, importance: float = 0.5) -> str:
        if category not in CATEGORIES:
            category = "personal_fact"
        embedding = _compute_embedding(content)
        entries = self.load_facts()
        for e in entries:
            if e.category == category and _word_overlap(e.content, content) > 0.6:
                e.content    = content
                e.timestamp  = datetime.datetime.now().isoformat()
                e.importance = max(e.importance, importance)
                e.embedding  = embedding
                self.save_facts(entries)
                return f"Updated [{category}]: {content[:80]}"

        entry = self.create_fact(category, content, importance)
        return f"Gespeichert [{category}]: {content[:80]}"

    def load_ego_state(self) -> dict:
        with self._lock:
            row = self._db.execute("SELECT energy, ts FROM ego_state WHERE id = 1").fetchone()
        if row:
            return {"energy": row[0], "ts": row[1]}
        return {"energy": 0.65}

    def save_ego_state(self, energy: float):
        ts = datetime.datetime.now().isoformat()
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO ego_state (id, energy, ts) VALUES (1, ?, ?)",
                (energy, ts),
            )
            self._db.commit()
        self._queue_drive_sync("ego_state.json", json.dumps({"energy": energy, "ts": ts}))

    def save_transcript(self, transcript: str):
        ts = datetime.datetime.now().isoformat()
        with self._lock:
            self._db.execute(
                "INSERT INTO transcripts (text, ts) VALUES (?, ?)",
                (transcript, ts),
            )
            self._db.commit()
        ts_file = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        self._queue_drive_sync(f"transcripts/{ts_file}.txt", transcript)

    def load_last_summary(self) -> str:
        with self._lock:
            row = self._db.execute("SELECT text FROM summaries ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else ""

    def save_summary(self, summary: str):
        ts = datetime.datetime.now().isoformat()
        with self._lock:
            self._db.execute(
                "INSERT INTO summaries (text, ts) VALUES (?, ?)",
                (summary, ts),
            )
            self._db.commit()
        self._queue_drive_sync("last_summary.json", json.dumps({"text": summary, "ts": ts}, ensure_ascii=False))

    def save_session(self, duration: int, turns: int, memory_saves: int, energy: float):
        ts = datetime.datetime.now().isoformat()
        with self._lock:
            self._db.execute(
                "INSERT INTO sessions (ts, duration, turns, memory_saves, energy) VALUES (?, ?, ?, ?, ?)",
                (ts, duration, turns, memory_saves, energy),
            )
            self._db.commit()

    def load_sessions(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT ts, duration, turns, memory_saves, energy FROM sessions ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {"ts": r[0], "duration": r[1], "turns": r[2], "memorySaves": r[3], "energy": r[4]}
            for r in rows
        ]

    def semantic_search(self, query: str, top_k: int = 6) -> list[MemoryEntry]:
        facts = self.load_facts()
        if not facts:
            return []

        query_embedding = _compute_embedding(query)
        scored: list[tuple[float, MemoryEntry]] = []

        for fact in facts:
            if fact.embedding and query_embedding:
                score = _cosine_similarity(query_embedding, fact.embedding)
            else:
                score = _keyword_score(query, fact.content) * 0.7

            score += fact.importance * 0.05
            scored.append((score, fact))

        scored.sort(key=lambda x: (x[0], x[1].timestamp), reverse=True)
        return [fact for _, fact in scored[:top_k]]

    def load_context(self) -> MemoryContext:
        ego = self.load_ego_state()
        return MemoryContext(
            facts=self.load_facts(),
            ego_energy=ego.get("energy", 0.65),
            last_summary=self.load_last_summary(),
            last_seen=ego.get("ts", ""),
        )

    def get_facts_by_category(self) -> dict[str, list[dict]]:
        facts = self.load_facts()
        by_cat: dict[str, list[dict]] = {}
        for f in facts:
            by_cat.setdefault(f.category, []).append({
                "content": f.content,
                "timestamp": f.timestamp,
                "importance": f.importance,
            })
        return by_cat

    # ── DRIVE SYNC QUEUE ──────────────────────────────────────────────────────

    def _queue_drive_sync(self, path: str, payload: str):
        if not self._svc:
            return
        with self._lock:
            self._db.execute(
                "INSERT INTO sync_queue (operation, path, payload, created_at) VALUES ('write', ?, ?, ?)",
                (path, payload, datetime.datetime.now().isoformat()),
            )
            self._db.commit()

    def _process_sync_queue(self):
        import time
        while True:
            time.sleep(10)
            if not self._svc:
                continue
            with self._lock:
                rows = self._db.execute(
                    "SELECT id, operation, path, payload FROM sync_queue WHERE synced = 0 ORDER BY id LIMIT 10"
                ).fetchall()
            if not rows:
                continue
            for row_id, op, path, payload in rows:
                try:
                    if path.endswith(".json"):
                        self._drive_write_json(path, json.loads(payload))
                    else:
                        self._drive_write_text(path, payload)
                    with self._lock:
                        self._db.execute("UPDATE sync_queue SET synced = 1 WHERE id = ?", (row_id,))
                        self._db.commit()
                except Exception as e:
                    print(f"[Memory] Drive-Sync Fehler ({path}): {e}")

    # ── DRIVE I/O (privat, nur für Backup) ────────────────────────────────────

    def _ensure_folder(self, name: str, parent_id: str) -> str:
        result = self._svc.files().list(
            q=(
                f"'{parent_id}' in parents and name='{name}' "
                "and mimeType='application/vnd.google-apps.folder' "
                "and trashed=false"
            ),
            fields="files(id)", pageSize=1,
        ).execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
        folder = self._svc.files().create(
            body={
                "name": name,
                "mimeType": "application/vnd.google-apps.folder",
                "parents": [parent_id],
            },
            fields="id",
        ).execute()
        return folder["id"]

    def _resolve(self, path: str) -> tuple[str, str]:
        parts = path.split("/")
        parent = self._folder_id
        for part in parts[:-1]:
            parent = self._ensure_folder(part, parent)
        return parent, parts[-1]

    def _get_file_id(self, filename: str, parent_id: str) -> Optional[str]:
        result = self._svc.files().list(
            q=f"'{parent_id}' in parents and name='{filename}' and trashed=false",
            fields="files(id)", pageSize=1,
        ).execute()
        files = result.get("files", [])
        return files[0]["id"] if files else None

    def _drive_read_json(self, path: str) -> Optional[dict | list]:
        if not self._svc:
            return None
        try:
            parent_id, filename = self._resolve(path)
            fid = self._get_file_id(filename, parent_id)
            if not fid:
                return None
            raw = self._svc.files().get_media(fileId=fid).execute()
            return json.loads(raw)
        except Exception as e:
            print(f"[Memory] Drive-Lesefehler {path}: {e}")
            return None

    def _drive_write_json(self, path: str, data: dict | list):
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._drive_write_raw(path, payload, "application/json")

    def _drive_write_text(self, path: str, text: str):
        self._drive_write_raw(path, text.encode("utf-8"), "text/plain")

    def _drive_write_raw(self, path: str, data: bytes, mime: str):
        if not self._svc:
            return
        try:
            parent_id, filename = self._resolve(path)
            media = MediaInMemoryUpload(data, mimetype=mime)
            fid = self._get_file_id(filename, parent_id)

            if fid and mime == "application/json":
                self._svc.files().update(fileId=fid, media_body=media).execute()
            else:
                self._svc.files().create(
                    body={"name": filename, "parents": [parent_id]},
                    media_body=media,
                ).execute()
        except Exception as e:
            print(f"[Memory] Drive-Schreibfehler {path}: {e}")

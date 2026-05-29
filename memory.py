"""
memory.py – Persistente Google Drive Memory für Claire.

Implementiert die Memory 2.0 Architektur aus dem Claire V2 Dossier:
  • 7 Kategorien
  • Duplikatschutz: >60% Wort-Überschneidung → Update (Patch) statt Insert (Post)
  • Retrieval: neueste Einträge zuerst, max. N pro Kategorie
  • Fallback: vollständig In-Memory wenn Drive nicht konfiguriert

Auth: Ausschließlich Application Default Credentials (ADC).
  Lokal:     gcloud auth application-default login
  Cloud Run: Service-Account via Workload Identity – kein Key-File nötig.
"""
import json
import os
import datetime
from dataclasses import dataclass, field
from typing import Optional

try:
    import google.auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaInMemoryUpload
    _DRIVE_OK = True
except ImportError:
    _DRIVE_OK = False


# ── SCHEMA ────────────────────────────────────────────────────────────────────

CATEGORIES = [
    "personal_fact",    # Fakten über Kev (Job, Wohnort, Familie …)
    "emotional_state",  # Kevs Stimmung & Gefühle
    "relationship",     # Beziehungsdynamik (Sophie, Freunde …)
    "past_event",       # Vergangene Events & Gespräche
    "preference",       # Vorlieben & Abneigungen
    "goal",             # Ziele & Pläne
    "episode",          # Einzelne prägende Episoden
]


@dataclass
class MemoryEntry:
    category: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    importance: float = 0.5
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category":   self.category,
            "content":    self.content,
            "timestamp":  self.timestamp,
            "importance": self.importance,
            "tags":       self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(
            category=d.get("category", "personal_fact"),
            content=d.get("content", ""),
            timestamp=d.get("timestamp", datetime.datetime.now().isoformat()),
            importance=float(d.get("importance", 0.5)),
            tags=d.get("tags", []),
        )


@dataclass
class MemoryContext:
    facts: list[MemoryEntry] = field(default_factory=list)
    ego_energy: float = 0.65
    last_summary: str = ""

    def to_prompt_string(self, max_per_cat: int = 5) -> str:
        """Kompakter String für den System-Prompt."""
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


# ── DUPLIKATSCHUTZ (>60% Wort-Überschneidung = Update) ───────────────────────

def _word_overlap(a: str, b: str) -> float:
    wa = set(a.lower().split())
    wb = set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / max(len(wa), len(wb))


# ── DRIVE MEMORY ──────────────────────────────────────────────────────────────

class DriveMemory:
    """
    Google Drive-backed persistente Memory.
    Fällt automatisch auf In-Memory zurück wenn Drive nicht konfiguriert.

    Ordnerstruktur in Drive:
      <GDRIVE_MEMORY_FOLDER_ID>/
        facts.json
        ego_state.json
        last_summary.json
        transcripts/
          2026-05-28_14-30.txt
    """

    _SCOPES = ["https://www.googleapis.com/auth/drive"]

    def __init__(self):
        self._folder_id = os.getenv("GDRIVE_MEMORY_FOLDER_ID")
        self._svc = None
        self._local: dict[str, object] = {}   # In-Memory Fallback

        if _DRIVE_OK and self._folder_id:
            try:
                # ADC: lokal via `gcloud auth application-default login`,
                # auf Cloud Run via Workload Identity – kein Key-File nötig.
                creds, _ = google.auth.default(scopes=self._SCOPES)
                self._svc = build("drive", "v3", credentials=creds)
                print("[Memory] Google Drive verbunden ✓  (ADC)")
            except Exception as e:
                print(f"[Memory] Drive-Init fehlgeschlagen ({e}) – Fallback: In-Memory")
        else:
            print("[Memory] Drive nicht konfiguriert – Fallback: In-Memory")

    # ── PUBLIC API ─────────────────────────────────────────────────────────────

    def load_facts(self) -> list[MemoryEntry]:
        raw = self._read_json("facts.json")
        if not isinstance(raw, list):
            return []
        return [MemoryEntry.from_dict(e) for e in raw if "content" in e]

    def save_facts(self, entries: list[MemoryEntry]):
        self._write_json("facts.json", [e.to_dict() for e in entries])

    def upsert_fact(self, category: str, content: str, importance: float = 0.5) -> str:
        """
        Insert oder Update.
        >60% Wort-Überschneidung innerhalb derselben Kategorie → Patch (kein Duplikat).
        """
        if category not in CATEGORIES:
            category = "personal_fact"

        entries = self.load_facts()
        for e in entries:
            if e.category == category and _word_overlap(e.content, content) > 0.6:
                e.content    = content
                e.timestamp  = datetime.datetime.now().isoformat()
                e.importance = max(e.importance, importance)
                self.save_facts(entries)
                return f"Updated [{category}]: {content[:80]}"

        entries.append(MemoryEntry(category=category, content=content, importance=importance))
        self.save_facts(entries)
        return f"Gespeichert [{category}]: {content[:80]}"

    def load_ego_state(self) -> dict:
        return self._read_json("ego_state.json") or {"energy": 0.65}

    def save_ego_state(self, energy: float):
        self._write_json("ego_state.json", {
            "energy": energy,
            "ts": datetime.datetime.now().isoformat(),
        })

    def save_transcript(self, transcript: str):
        ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        self._write_text(f"transcripts/{ts}.txt", transcript)

    def load_last_summary(self) -> str:
        data = self._read_json("last_summary.json")
        return data.get("text", "") if isinstance(data, dict) else ""

    def save_summary(self, summary: str):
        self._write_json("last_summary.json", {
            "text": summary,
            "ts": datetime.datetime.now().isoformat(),
        })

    def load_context(self) -> MemoryContext:
        ego = self.load_ego_state()
        return MemoryContext(
            facts=self.load_facts(),
            ego_energy=ego.get("energy", 0.65),
            last_summary=self.load_last_summary(),
        )

    # ── DRIVE I/O (privat) ────────────────────────────────────────────────────

    def _ensure_folder(self, name: str, parent_id: str) -> str:
        """Gibt ID eines Unterordners zurück, legt ihn an falls nötig."""
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
        """Gibt (parent_folder_id, filename) für 'transcripts/foo.txt' zurück."""
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

    def _read_json(self, path: str) -> Optional[dict | list]:
        if not self._svc:
            return self._local.get(path)
        try:
            parent_id, filename = self._resolve(path)
            fid = self._get_file_id(filename, parent_id)
            if not fid:
                return None
            raw = self._svc.files().get_media(fileId=fid).execute()
            return json.loads(raw)
        except Exception as e:
            print(f"[Memory] Lesefehler {path}: {e}")
            return None

    def _write_json(self, path: str, data: dict | list):
        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self._write_raw(path, payload, "application/json")

    def _write_text(self, path: str, text: str):
        self._write_raw(path, text.encode("utf-8"), "text/plain")

    def _write_raw(self, path: str, data: bytes, mime: str):
        # In-Memory Fallback
        if not self._svc:
            self._local[path] = (
                json.loads(data) if mime == "application/json" else data.decode()
            )
            return
        try:
            parent_id, filename = self._resolve(path)
            media = MediaInMemoryUpload(data, mimetype=mime)
            fid = self._get_file_id(filename, parent_id)

            if fid and mime == "application/json":
                # Update bestehende Datei
                self._svc.files().update(fileId=fid, media_body=media).execute()
            else:
                # Neue Datei (immer für Transkripte)
                self._svc.files().create(
                    body={"name": filename, "parents": [parent_id]},
                    media_body=media,
                ).execute()
        except Exception as e:
            print(f"[Memory] Schreibfehler {path}: {e}")

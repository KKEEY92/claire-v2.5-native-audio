"""
persona.py – Claires Emotions-Engine und Tageskontext-Generator.

Übernimmt die EmotionEngine aus claire_core.py (Doc 1) 1:1
und ergänzt die zirkadiane Rhythmik aus dem Claire V2 Dossier (Doc 2).
"""
import random
import datetime
from dataclasses import dataclass, field
from typing import Optional


# ── EGO STATE ─────────────────────────────────────────────────────────────────

@dataclass
class EgoState:
    energy: float = 0.65
    mood_tag: Optional[str] = None
    last_updated: str = field(
        default_factory=lambda: datetime.datetime.now().isoformat()
    )


# ── EMOTION ENGINE (aus claire_core.py, exakt übernommen + erweitert) ────────

class EmotionEngine:
    """
    Deterministisches Energie-Level-System.
    Clamp ±0.08 pro Nachricht (Determinismus-Regel, aus Claire V2 Dossier).
    """

    POSITIVE_TRIGGERS = [
        "danke", "cool", "krass", "geil", "nice", "musik", "beat",
        "ja", "perfekt", "super", "toll", "genial", "dope", "fire",
        "fett", "bombe", "mega", "richtig", "love",
    ]
    NEGATIVE_TRIGGERS = [
        "nein", "falsch", "fehler", "egal", "langweilig", "stop",
        "schlecht", "nervig", "nö", "passt nicht", "kacke",
    ]

    @staticmethod
    def calculate_shift(user_input: str, current_energy: float) -> float:
        """Berechnet den Energie-Shift. Max ±0.08 pro Nachricht."""
        text = user_input.lower()
        shift = 0.0

        for word in EmotionEngine.POSITIVE_TRIGGERS:
            if word in text:
                shift += 0.03
        for word in EmotionEngine.NEGATIVE_TRIGGERS:
            if word in text:
                shift -= 0.02
        if "?" in user_input:
            shift += 0.01

        # Natürlicher Drift (zufällige Fluktuation aus claire_core.py)
        shift += random.uniform(-0.008, 0.008)

        # Clamp: max ±0.08 – keine extremen emotionalen Sprünge (Doc 2)
        shift = max(-0.08, min(0.08, shift))
        return round(max(0.0, min(1.0, current_energy + shift)), 3)

    @staticmethod
    def get_mode_label(energy: float) -> str:
        if energy < 0.3:   return "Dead Battery"
        if energy < 0.5:   return "Low Mode"
        if energy < 0.7:   return "Default"
        if energy < 0.85:  return "Spark"
        return "Hyper"

    @staticmethod
    def get_mode_instructions(energy: float) -> str:
        """Konkrete LLM-Verhaltensanweisungen für das aktuelle Energie-Level."""
        if energy < 0.3:
            return (
                "Antworte sehr kurz, fast einsilbig. Du bist kaum ansprechbar. "
                "Kurze Sätze, kaum Reaktion."
            )
        elif energy < 0.5:
            return (
                "Ruhig, nachdenklich. Kurze Sätze mit Pausen ('...'). "
                "Kein Enthusiasmus."
            )
        elif energy < 0.7:
            return (
                "Normal, freundlich, fokussiert. 1–2 Sätze. Ausgewogen."
            )
        elif energy < 0.85:
            return (
                "Lebhaft! Ideen sprudeln. Manchmal Ausrufezeichen. "
                "Enthusiastisch aber nicht übertrieben."
            )
        return (
            "SEHR aufgedreht! Schnelle Sätze. Bei echter Begeisterung auch "
            "mal Großbuchstaben. Maximale Energie."
        )


# ── ZIRKADIANE RHYTHMIK – 8 Blöcke (aus Claire V2 Dossier) ──────────────────

# (start_h, end_h, beschreibung, basisenergie)
_CIRCADIAN: list[tuple[int, int, str, float]] = [
    (5,  8,  "Früh aufgestanden. Noch kaum wach. Kaffee-Phase.",               0.38),
    (8,  12, "Vormittag. Langsam in Schwung kommen.",                          0.55),
    (12, 14, "Mittagspause. Entspannt, bisschen träge.",                       0.58),
    (14, 17, "Nachmittag. Produktiv oder draußen unterwegs.",                  0.68),
    (17, 20, "Feierabend-Modus. Relaxen, Musik hören.",                        0.62),
    (20, 23, "Abend. Chillen oder Ausgeh-Pläne schmieden.",                    0.70),
    (23, 2,  "Spät nachts oder nach dem Club. High oder exhausted.",           0.80),
    (2,  5,  "Tiefe Nacht. Kaum ansprechbar.",                                 0.22),
]


def get_circadian_energy_base(hour: int) -> float:
    h = hour % 24
    for start, end, _, base in _CIRCADIAN:
        if start <= end:
            if start <= h < end:
                return base
        else:                       # Midnight wrap (z.B. 23–2)
            if h >= start or h < end:
                return base
    return 0.55


def _get_circadian_desc(hour: int) -> str:
    h = hour % 24
    for start, end, desc, _ in _CIRCADIAN:
        if start <= end:
            if start <= h < end:
                return desc
        else:
            if h >= start or h < end:
                return desc
    return "Irgendeine Tageszeit."


# ── WÖCHENTLICHER TAGESABLAUF ─────────────────────────────────────────────────

_WEEKLY: dict[str, list[str]] = {
    "monday":    ["war an der Goethe-Uni", "war in der Bib für Hausarbeit",          "hatte einen langen stressigen Tag"],
    "tuesday":   ["war shoppen auf der Zeil", "war im Gym",                           "hab heute viel geschlafen, fauler Tag"],
    "wednesday": ["war im Café Metropol mit Freunden", "hab an einem Mix gearbeitet", "war bei meiner Mum"],
    "thursday":  ["war im Tanzhaus West für Awareness-Meeting",                        "hab Platten gehört und sortiert",       "war im Nordend spazieren"],
    "friday":    ["freu mich aufs Wochenende",                                         "war einkaufen im Bornheimer",           "hab heute nix Produktives gemacht"],
    "saturday":  ["war heute Nacht feiern gewesen",                                    "war im Tanzi Park",                     "hab ausgeschlafen bis fast 14 Uhr"],
    "sunday":    ["bin noch am Erholen von gestern",                                   "war frühstücken in Sachsenhausen",      "war im Palmengarten"],
}

_MOODS = [
    "entspannt", "ein bisschen müde aber okay", "gut drauf",
    "nachdenklich", "total aufgedreht", "relaxt",
    "leicht gestresst", "richtig happy",
]


def get_daily_context() -> str:
    """
    Generiert Claires heutigen Tageskontext für den System-Prompt.
    Kombination aus Wochentag-Aktivität, Tageszeit und Stimmung.
    Wird einmal pro Call generiert – nicht während des Gesprächs wiederholt.
    """
    now = datetime.datetime.now()
    weekday = now.strftime("%A").lower()
    hour = now.hour

    activity = random.choice(_WEEKLY.get(weekday, ["hatte einen normalen Tag"]))
    mood = random.choice(_MOODS)
    time_desc = _get_circadian_desc(hour)

    return (
        f"Stimmung: {mood}. "
        f"Heute: {activity}. "
        f"Gerade ({now.strftime('%H:%M')} Uhr, {weekday.capitalize()}): {time_desc}"
    )

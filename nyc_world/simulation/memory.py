"""Structured NPC memory and opinion synthesis."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class MemoryFact:
    """A single remembered interaction or observation."""

    id: str
    category: str
    summary: str
    tick: int
    game_day: int
    game_time: str
    target_id: str = ""
    amount: int = 0
    sentiment: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "summary": self.summary,
            "tick": self.tick,
            "game_day": self.game_day,
            "game_time": self.game_time,
            "target_id": self.target_id,
            "amount": self.amount,
            "sentiment": self.sentiment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MemoryFact:
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            category=data["category"],
            summary=data["summary"],
            tick=data.get("tick", 0),
            game_day=data.get("game_day", 1),
            game_time=data.get("game_time", ""),
            target_id=data.get("target_id", ""),
            amount=data.get("amount", 0),
            sentiment=data.get("sentiment", 0.0),
        )


def make_fact(
    category: str,
    summary: str,
    *,
    tick: int,
    game_day: int,
    game_time: str,
    target_id: str = "",
    amount: int = 0,
    sentiment: float = 0.0,
) -> MemoryFact:
    return MemoryFact(
        id=str(uuid.uuid4())[:8],
        category=category,
        summary=summary,
        tick=tick,
        game_day=game_day,
        game_time=game_time,
        target_id=target_id,
        amount=amount,
        sentiment=sentiment,
    )


def synthesize_opinion(trust: float, friendship: float, facts: list[MemoryFact]) -> str:
    """Rule-based opinion text — always works offline."""
    helped = sum(1 for f in facts if f.category in ("helped", "quest_complete", "gave"))
    stole = sum(1 for f in facts if f.category == "stole")
    visited = sum(1 for f in facts if f.category == "visited")

    lines: list[str] = []

    if trust >= 70 and friendship >= 55 and stole == 0:
        lines.append('"Generally helpful."')
    elif trust >= 50 and stole == 0:
        lines.append('"Friendly enough."')
    elif stole > 0 and trust >= 40:
        lines.append('"Generally helpful."')
        lines.append(' "Slightly suspicious."')
    elif stole > 0:
        lines.append('"Do not trust you."')
    elif trust < 30:
        lines.append('"Keeps their distance."')
    else:
        lines.append('"Still figuring you out."')

    if visited >= 3 and friendship >= 45:
        lines.append(' "Feels like a regular."')

    return "\n".join(lines)


def format_memory_panel(
    display_name: str,
    *,
    met_day: int,
    met_time: str,
    trust: float,
    friendship: float,
    visit_count: int,
    last_seen: str,
    facts: list[MemoryFact],
    opinion: str,
) -> list[str]:
    """HUD lines for NPC memory panel."""
    lines = [
        f"Met you: Day {met_day}, {met_time}",
        f"Trust: {int(round(trust))}    Friendship: {int(round(friendship))}",
        f"Last seen: {last_seen} · Visits: {visit_count}",
        "",
        "MEMORIES",
    ]
    if facts:
        for fact in facts[-8:]:
            mark = "✓" if fact.sentiment >= 0 else "✗"
            lines.append(f" {mark} {fact.summary}  (Day {fact.game_day})")
    else:
        lines.append(" (none yet)")
    lines.extend(["", "OPINION", opinion])
    return lines

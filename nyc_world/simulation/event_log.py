"""Append-only canonical event timeline for simulation replay and mysteries."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EventLogEntry:
    tick: int
    game_day: int
    game_time: str
    actor_id: str
    action: str
    location_id: str = ""
    details: str = ""
    visibility: str = "public"

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "game_day": self.game_day,
            "game_time": self.game_time,
            "actor_id": self.actor_id,
            "action": self.action,
            "location_id": self.location_id,
            "details": self.details,
            "visibility": self.visibility,
        }

    @classmethod
    def from_dict(cls, data: dict) -> EventLogEntry:
        return cls(
            tick=data.get("tick", 0),
            game_day=data.get("game_day", 1),
            game_time=data.get("game_time", ""),
            actor_id=data.get("actor_id", ""),
            action=data.get("action", ""),
            location_id=data.get("location_id", ""),
            details=data.get("details", ""),
            visibility=data.get("visibility", "public"),
        )


@dataclass
class EventLog:
    entries: list[EventLogEntry] = field(default_factory=list)
    _max_entries: int = 10_000

    def append(
        self,
        *,
        tick: int,
        game_day: int,
        game_time: str,
        actor_id: str,
        action: str,
        location_id: str = "",
        details: str = "",
        visibility: str = "public",
    ) -> EventLogEntry:
        entry = EventLogEntry(
            tick=tick,
            game_day=game_day,
            game_time=game_time,
            actor_id=actor_id,
            action=action,
            location_id=location_id,
            details=details,
            visibility=visibility,
        )
        self.entries.append(entry)
        if len(self.entries) > self._max_entries:
            self.entries = self.entries[-self._max_entries :]
        return entry

    def recent(self, count: int = 20, *, visibility: str | None = None) -> list[EventLogEntry]:
        items = self.entries
        if visibility:
            items = [e for e in items if e.visibility == visibility]
        return items[-count:]

    def to_dict(self) -> dict:
        return {"entries": [e.to_dict() for e in self.entries]}

    @classmethod
    def from_dict(cls, data: dict) -> EventLog:
        log = cls()
        log.entries = [EventLogEntry.from_dict(e) for e in data.get("entries", [])]
        return log

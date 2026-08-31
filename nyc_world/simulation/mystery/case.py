"""Mystery case data — ground truth hidden from player until solved."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.simulation.event_log import EventLog, EventLogEntry


@dataclass
class MysteryCase:
    """Ground truth for a procedural mystery — never shown directly to player."""

    mystery_id: str
    title: str
    seed: int
    crime_type: str
    victim_id: str
    culprit_id: str
    stolen_item: str
    crime_location: str
    crime_time: str
    crime_day: int
    backstory_log: EventLog = field(default_factory=EventLog)

    def to_dict(self) -> dict:
        return {
            "mystery_id": self.mystery_id,
            "title": self.title,
            "seed": self.seed,
            "crime_type": self.crime_type,
            "victim_id": self.victim_id,
            "culprit_id": self.culprit_id,
            "stolen_item": self.stolen_item,
            "crime_location": self.crime_location,
            "crime_time": self.crime_time,
            "crime_day": self.crime_day,
            "backstory_log": self.backstory_log.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> MysteryCase:
        return cls(
            mystery_id=data["mystery_id"],
            title=data.get("title", "The Midnight Disappearance"),
            seed=data.get("seed", 0),
            crime_type=data.get("crime_type", "theft"),
            victim_id=data.get("victim_id", "maya"),
            culprit_id=data.get("culprit_id", "alex"),
            stolen_item=data.get("stolen_item", "camera"),
            crime_location=data.get("crime_location", "cafe_village"),
            crime_time=data.get("crime_time", "11:42 PM"),
            crime_day=data.get("crime_day", 1),
            backstory_log=EventLog.from_dict(data.get("backstory_log", {})),
        )


@dataclass
class MysteryInvestigation:
    """Player-facing investigation state."""

    case: MysteryCase
    discovered_entry_ids: set[str] = field(default_factory=set)
    solved: bool = False
    accused_id: str | None = None

    def entry_id(self, entry: EventLogEntry) -> str:
        return f"{entry.tick}:{entry.actor_id}:{entry.action}:{entry.location_id}"

    def discover(self, entry: EventLogEntry) -> bool:
        eid = self.entry_id(entry)
        if eid in self.discovered_entry_ids:
            return False
        self.discovered_entry_ids.add(eid)
        return True

    def discovered_entries(self) -> list[EventLogEntry]:
        entries = []
        for entry in self.case.backstory_log.entries:
            if self.entry_id(entry) in self.discovered_entry_ids:
                entries.append(entry)
        return sorted(entries, key=lambda e: (e.game_day, e.game_time, e.tick))

    def try_accuse(self, suspect_id: str) -> tuple[bool, str]:
        self.accused_id = suspect_id
        if suspect_id == self.case.culprit_id:
            self.solved = True
            return True, f"Correct! {suspect_id.title()} took the {self.case.stolen_item}."
        return False, f"{suspect_id.title()} wasn't the thief. Keep investigating."

    def to_dict(self) -> dict:
        return {
            "case": self.case.to_dict(),
            "discovered_entry_ids": sorted(self.discovered_entry_ids),
            "solved": self.solved,
            "accused_id": self.accused_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MysteryInvestigation:
        inv = cls(case=MysteryCase.from_dict(data["case"]))
        inv.discovered_entry_ids = set(data.get("discovered_entry_ids", []))
        inv.solved = data.get("solved", False)
        inv.accused_id = data.get("accused_id")
        return inv

"""Public NPC definition types for mod authors."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Personality:
    curiosity: float = 0.5
    kindness: float = 0.5
    extroversion: float = 0.5
    risk_tolerance: float = 0.5
    ambition: float = 0.5

    def to_dict(self) -> dict:
        return {
            "curiosity": self.curiosity,
            "kindness": self.kindness,
            "extroversion": self.extroversion,
            "risk_tolerance": self.risk_tolerance,
            "ambition": self.ambition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Personality:
        return cls(
            curiosity=data.get("curiosity", 0.5),
            kindness=data.get("kindness", 0.5),
            extroversion=data.get("extroversion", 0.5),
            risk_tolerance=data.get("risk_tolerance", 0.5),
            ambition=data.get("ambition", 0.5),
        )


@dataclass
class Needs:
    money: float = 0.4
    hunger: float = 0.3
    energy: float = 0.5
    social: float = 0.4

    def to_dict(self) -> dict:
        return {
            "money": self.money,
            "hunger": self.hunger,
            "energy": self.energy,
            "social": self.social,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Needs:
        return cls(
            money=data.get("money", 0.4),
            hunger=data.get("hunger", 0.3),
            energy=data.get("energy", 0.5),
            social=data.get("social", 0.4),
        )


@dataclass
class ScheduleStop:
    hour: int
    minute: int
    location_id: str
    label: str = ""

    def to_dict(self) -> dict:
        return {
            "hour": self.hour,
            "minute": self.minute,
            "location_id": self.location_id,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ScheduleStop:
        return cls(
            hour=data.get("hour", 9),
            minute=data.get("minute", 0),
            location_id=data.get("location_id", ""),
            label=data.get("label", ""),
        )


@dataclass
class Schedule:
    stops: list[ScheduleStop] = field(default_factory=list)

    @classmethod
    def workplace(cls, location_id: str, hour: int = 9, minute: int = 0) -> Schedule:
        return cls(
            stops=[
                ScheduleStop(hour, minute, location_id, "work"),
                ScheduleStop(18, 0, location_id, "close"),
            ]
        )

    def to_dict(self) -> dict:
        return {"stops": [s.to_dict() for s in self.stops]}

    @classmethod
    def from_dict(cls, data: dict) -> Schedule:
        return cls(stops=[ScheduleStop.from_dict(s) for s in data.get("stops", [])])


@dataclass
class NPC:
    """Mod-authored NPC — converted into city simulation entities on register."""

    id: str
    name: str
    personality: Personality = field(default_factory=Personality)
    needs: Needs = field(default_factory=Needs)
    schedule: Schedule = field(default_factory=Schedule)
    dialogue_pack: str = ""
    x: float | None = None
    z: float | None = None
    speed: float = 1.2
    color: tuple[float, float, float] = (0.65, 0.45, 0.85)
    interactable: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "personality": self.personality.to_dict(),
            "needs": self.needs.to_dict(),
            "schedule": self.schedule.to_dict(),
            "dialogue_pack": self.dialogue_pack,
            "x": self.x,
            "z": self.z,
            "speed": self.speed,
            "color": list(self.color),
            "interactable": self.interactable,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPC:
        color = data.get("color", [0.65, 0.45, 0.85])
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            personality=Personality.from_dict(data.get("personality", {})),
            needs=Needs.from_dict(data.get("needs", {})),
            schedule=Schedule.from_dict(data.get("schedule", {})),
            dialogue_pack=data.get("dialogue_pack", ""),
            x=data.get("x"),
            z=data.get("z"),
            speed=data.get("speed", 1.2),
            color=(float(color[0]), float(color[1]), float(color[2])),
            interactable=data.get("interactable", True),
        )

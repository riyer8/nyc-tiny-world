"""Serializable world state snapshots for simulation and ML."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ClockState:
    hour: int = 8
    minute: int = 0
    weather: str = "clear"
    tick: int = 0

    def to_dict(self) -> dict:
        return {"hour": self.hour, "minute": self.minute, "weather": self.weather, "tick": self.tick}

    @classmethod
    def from_dict(cls, data: dict) -> ClockState:
        return cls(
            hour=data.get("hour", 8),
            minute=data.get("minute", 0),
            weather=data.get("weather", "clear"),
            tick=data.get("tick", 0),
        )


@dataclass
class PlayerState:
    x: float = 0.0
    z: float = 0.0
    yaw: float = 0.0
    money: int = 37
    xp: int = 0
    items: dict[str, int] = field(default_factory=dict)
    relationships: dict[str, float] = field(default_factory=dict)
    in_interior: bool = False

    def to_dict(self) -> dict:
        return {
            "x": self.x,
            "z": self.z,
            "yaw": self.yaw,
            "money": self.money,
            "xp": self.xp,
            "items": dict(self.items),
            "relationships": dict(self.relationships),
            "in_interior": self.in_interior,
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerState:
        return cls(
            x=data.get("x", 0.0),
            z=data.get("z", 0.0),
            yaw=data.get("yaw", 0.0),
            money=data.get("money", 37),
            xp=data.get("xp", 0),
            items=dict(data.get("items", {})),
            relationships=dict(data.get("relationships", {})),
            in_interior=data.get("in_interior", False),
        )


@dataclass
class NPCState:
    id: str
    name: str
    x: float
    z: float
    personality: str = ""
    goal: str = ""
    mood: float = 0.5
    player_affinity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "z": self.z,
            "personality": self.personality,
            "goal": self.goal,
            "mood": self.mood,
            "player_affinity": self.player_affinity,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPCState:
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            x=data.get("x", 0.0),
            z=data.get("z", 0.0),
            personality=data.get("personality", ""),
            goal=data.get("goal", ""),
            mood=data.get("mood", 0.5),
            player_affinity=data.get("player_affinity", 0.0),
        )


@dataclass
class VehicleState:
    id: str
    kind: str
    x: float
    z: float

    def to_dict(self) -> dict:
        return {"id": self.id, "kind": self.kind, "x": self.x, "z": self.z}

    @classmethod
    def from_dict(cls, data: dict) -> VehicleState:
        return cls(
            id=data["id"],
            kind=data.get("kind", "car"),
            x=data.get("x", 0.0),
            z=data.get("z", 0.0),
        )


@dataclass
class QuestSnapshot:
    active_quest_id: str | None = None
    completed: list[str] = field(default_factory=list)
    current_objective: str | None = None

    def to_dict(self) -> dict:
        return {
            "active_quest_id": self.active_quest_id,
            "completed": list(self.completed),
            "current_objective": self.current_objective,
        }

    @classmethod
    def from_dict(cls, data: dict) -> QuestSnapshot:
        return cls(
            active_quest_id=data.get("active_quest_id"),
            completed=list(data.get("completed", [])),
            current_objective=data.get("current_objective"),
        )


@dataclass
class WorldState:
    tick: int = 0
    clock: ClockState = field(default_factory=ClockState)
    player: PlayerState = field(default_factory=PlayerState)
    npcs: list[NPCState] = field(default_factory=list)
    vehicles: list[VehicleState] = field(default_factory=list)
    quests: QuestSnapshot = field(default_factory=QuestSnapshot)
    building_count: int = 0
    npc_count: int = 0
    vehicle_count: int = 0

    def to_dict(self) -> dict:
        return {
            "tick": self.tick,
            "clock": self.clock.to_dict(),
            "player": self.player.to_dict(),
            "npcs": [n.to_dict() for n in self.npcs],
            "vehicles": [v.to_dict() for v in self.vehicles],
            "quests": self.quests.to_dict(),
            "building_count": self.building_count,
            "npc_count": self.npc_count,
            "vehicle_count": self.vehicle_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorldState:
        return cls(
            tick=data.get("tick", 0),
            clock=ClockState.from_dict(data.get("clock", {})),
            player=PlayerState.from_dict(data.get("player", {})),
            npcs=[NPCState.from_dict(n) for n in data.get("npcs", [])],
            vehicles=[VehicleState.from_dict(v) for v in data.get("vehicles", [])],
            quests=QuestSnapshot.from_dict(data.get("quests", {})),
            building_count=data.get("building_count", 0),
            npc_count=data.get("npc_count", 0),
            vehicle_count=data.get("vehicle_count", 0),
        )

    def npc_by_id(self, npc_id: str) -> NPCState | None:
        for npc in self.npcs:
            if npc.id == npc_id or npc.name == npc_id:
                return npc
        return None

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
    trust: float = 50.0
    friendship: float = 30.0
    visit_count: int = 0
    hunger: float = 0.0
    energy: float = 0.0
    social_need: float = 0.0
    money_need: float = 0.0
    current_action: str = ""
    plan_summary: str = ""

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
            "trust": self.trust,
            "friendship": self.friendship,
            "visit_count": self.visit_count,
            "hunger": self.hunger,
            "energy": self.energy,
            "social_need": self.social_need,
            "money_need": self.money_need,
            "current_action": self.current_action,
            "plan_summary": self.plan_summary,
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
            trust=data.get("trust", 50.0),
            friendship=data.get("friendship", 30.0),
            visit_count=data.get("visit_count", 0),
            hunger=data.get("hunger", 0.0),
            energy=data.get("energy", 0.0),
            social_need=data.get("social_need", 0.0),
            money_need=data.get("money_need", 0.0),
            current_action=data.get("current_action", ""),
            plan_summary=data.get("plan_summary", ""),
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
    generated_ids: list[str] = field(default_factory=list)
    available_generated: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "active_quest_id": self.active_quest_id,
            "completed": list(self.completed),
            "current_objective": self.current_objective,
            "generated_ids": list(self.generated_ids),
            "available_generated": list(self.available_generated),
        }

    @classmethod
    def from_dict(cls, data: dict) -> QuestSnapshot:
        return cls(
            active_quest_id=data.get("active_quest_id"),
            completed=list(data.get("completed", [])),
            current_objective=data.get("current_objective"),
            generated_ids=list(data.get("generated_ids", [])),
            available_generated=list(data.get("available_generated", [])),
        )


@dataclass
class RelationshipSnapshot:
    npc_id: str
    trust: float = 50.0
    friendship: float = 30.0
    opinion: str = ""
    visit_count: int = 0
    fact_count: int = 0

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "trust": self.trust,
            "friendship": self.friendship,
            "opinion": self.opinion,
            "visit_count": self.visit_count,
            "fact_count": self.fact_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipSnapshot:
        return cls(
            npc_id=data.get("npc_id", ""),
            trust=data.get("trust", 50.0),
            friendship=data.get("friendship", 30.0),
            opinion=data.get("opinion", ""),
            visit_count=data.get("visit_count", 0),
            fact_count=data.get("fact_count", 0),
        )


@dataclass
class EconomySnapshot:
    week: int = 1
    open_businesses: int = 0
    village_rent_index: float = 1.0
    journal_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "week": self.week,
            "open_businesses": self.open_businesses,
            "village_rent_index": self.village_rent_index,
            "journal_lines": list(self.journal_lines),
        }

    @classmethod
    def from_dict(cls, data: dict) -> EconomySnapshot:
        return cls(
            week=data.get("week", 1),
            open_businesses=data.get("open_businesses", 0),
            village_rent_index=data.get("village_rent_index", 1.0),
            journal_lines=list(data.get("journal_lines", [])),
        )


@dataclass
class MysterySnapshot:
    title: str = ""
    solved: bool = False
    clues_discovered: int = 0
    crime_time: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "solved": self.solved,
            "clues_discovered": self.clues_discovered,
            "crime_time": self.crime_time,
        }

    @classmethod
    def from_dict(cls, data: dict) -> MysterySnapshot:
        return cls(
            title=data.get("title", ""),
            solved=data.get("solved", False),
            clues_discovered=data.get("clues_discovered", 0),
            crime_time=data.get("crime_time", ""),
        )


@dataclass
class FeedSnapshot:
    weather: str | None = None
    transit_lines: list[str] = field(default_factory=list)
    banner_lines: list[str] = field(default_factory=list)
    subway_boarding_rate: float = 1.0
    transit_affected_npcs: int = 0

    def to_dict(self) -> dict:
        return {
            "weather": self.weather,
            "transit_lines": list(self.transit_lines),
            "banner_lines": list(self.banner_lines),
            "subway_boarding_rate": self.subway_boarding_rate,
            "transit_affected_npcs": self.transit_affected_npcs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> FeedSnapshot:
        return cls(
            weather=data.get("weather"),
            transit_lines=list(data.get("transit_lines", [])),
            banner_lines=list(data.get("banner_lines", [])),
            subway_boarding_rate=data.get("subway_boarding_rate", 1.0),
            transit_affected_npcs=data.get("transit_affected_npcs", 0),
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
    event_count: int = 0
    game_day: int = 1
    feeds: FeedSnapshot = field(default_factory=FeedSnapshot)
    relationships: list[RelationshipSnapshot] = field(default_factory=list)
    economy: EconomySnapshot = field(default_factory=EconomySnapshot)
    mystery: MysterySnapshot = field(default_factory=MysterySnapshot)
    mod_npc_ids: list[str] = field(default_factory=list)

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
            "event_count": self.event_count,
            "game_day": self.game_day,
            "feeds": self.feeds.to_dict(),
            "relationships": [r.to_dict() for r in self.relationships],
            "economy": self.economy.to_dict(),
            "mystery": self.mystery.to_dict(),
            "mod_npc_ids": list(self.mod_npc_ids),
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
            event_count=data.get("event_count", 0),
            game_day=data.get("game_day", 1),
            feeds=FeedSnapshot.from_dict(data.get("feeds", {})),
            relationships=[
                RelationshipSnapshot.from_dict(r) for r in data.get("relationships", [])
            ],
            economy=EconomySnapshot.from_dict(data.get("economy", {})),
            mystery=MysterySnapshot.from_dict(data.get("mystery", {})),
            mod_npc_ids=list(data.get("mod_npc_ids", [])),
        )

    def npc_by_id(self, npc_id: str) -> NPCState | None:
        for npc in self.npcs:
            if npc.id == npc_id or npc.name == npc_id:
                return npc
        return None

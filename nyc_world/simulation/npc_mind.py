"""NPC cognition — needs, goals, memory, and relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from nyc_world.simulation.memory import format_memory_panel

if TYPE_CHECKING:
    from nyc_world.simulation.relationships import RelationshipStore


class Need(str, Enum):
    SOCIAL = "social"
    REST = "rest"
    WORK = "work"
    COMFORT = "comfort"
    MONEY = "money"


@dataclass
class Goal:
    id: str
    description: str
    priority: float = 0.5


@dataclass
class Memory:
    event: str
    tick: int
    details: str = ""


@dataclass
class NPCMind:
    npc_id: str
    display_name: str
    workplace_id: str = ""
    home_hour: int = 18
    hates_rain: bool = False
    needs: dict[str, float] = field(default_factory=dict)
    goals: list[Goal] = field(default_factory=list)
    memories: list[Memory] = field(default_factory=list)
    npc_relationships: dict[str, float] = field(default_factory=dict)
    mood: float = 0.5

    def __post_init__(self) -> None:
        if not self.needs:
            self.needs = {n.value: 0.5 for n in Need}

    @property
    def player_affinity(self) -> float:
        return 0.0

    def remember(self, event: str, tick: int, details: str = "") -> None:
        self.memories.append(Memory(event, tick, details))
        if len(self.memories) > 32:
            self.memories.pop(0)

    def has_memory(self, event: str) -> bool:
        return any(m.event == event for m in self.memories)

    def adjust_need(self, need: Need | str, delta: float) -> None:
        key = need.value if isinstance(need, Need) else need
        self.needs[key] = max(0.0, min(1.0, self.needs.get(key, 0.5) + delta))

    def adjust_npc_relationship(self, other_id: str, delta: float) -> float:
        value = self.npc_relationships.get(other_id, 0.0) + delta
        self.npc_relationships[other_id] = max(-1.0, min(1.0, value))
        return self.npc_relationships[other_id]

    def current_goal_text(self) -> str:
        if not self.goals:
            return "wandering"
        return max(self.goals, key=lambda g: g.priority).description

    def mood_label(self) -> str:
        if self.mood >= 0.75:
            return "happy"
        if self.mood >= 0.55:
            return "content"
        if self.mood >= 0.35:
            return "neutral"
        if self.mood >= 0.15:
            return "unhappy"
        return "miserable"

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "display_name": self.display_name,
            "workplace_id": self.workplace_id,
            "home_hour": self.home_hour,
            "hates_rain": self.hates_rain,
            "needs": dict(self.needs),
            "goals": [{"id": g.id, "description": g.description, "priority": g.priority} for g in self.goals],
            "memories": [{"event": m.event, "tick": m.tick, "details": m.details} for m in self.memories],
            "npc_relationships": dict(self.npc_relationships),
            "mood": self.mood,
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPCMind:
        mind = cls(
            npc_id=data["npc_id"],
            display_name=data.get("display_name", data["npc_id"].title()),
            workplace_id=data.get("workplace_id", ""),
            home_hour=data.get("home_hour", 18),
            hates_rain=data.get("hates_rain", False),
            needs=dict(data.get("needs", {})),
            npc_relationships=dict(data.get("npc_relationships", {})),
            mood=data.get("mood", 0.5),
        )
        mind.goals = [
            Goal(g["id"], g["description"], g.get("priority", 0.5))
            for g in data.get("goals", [])
        ]
        mind.memories = [
            Memory(m["event"], m.get("tick", 0), m.get("details", ""))
            for m in data.get("memories", [])
        ]
        return mind


def create_maya_mind() -> NPCMind:
    return NPCMind(
        npc_id="maya",
        display_name="Maya",
        workplace_id="cafe_village",
        home_hour=18,
        hates_rain=True,
        needs={
            Need.SOCIAL.value: 0.6,
            Need.WORK.value: 0.7,
            Need.REST.value: 0.4,
            Need.COMFORT.value: 0.5,
            Need.MONEY.value: 0.72,
        },
        goals=[
            Goal("work_cafe", "Work at the Village Cafe", 0.6),
            Goal("earn_rent", "Earn enough for rent", 0.75),
        ],
        npc_relationships={"alex": 0.6},
    )


def create_alex_mind() -> NPCMind:
    return NPCMind(
        npc_id="alex",
        display_name="Alex",
        home_hour=22,
        hates_rain=False,
        needs={
            Need.SOCIAL.value: 0.5,
            Need.WORK.value: 0.3,
            Need.REST.value: 0.6,
            Need.COMFORT.value: 0.4,
            Need.MONEY.value: 0.35,
        },
        goals=[Goal("get_to_class", "Get to class on time", 0.7)],
        npc_relationships={"maya": 0.5},
    )


class NPCMindRegistry:
    """Maps NPC ids to cognitive profiles and player relationships."""

    def __init__(self, relationships: RelationshipStore | None = None) -> None:
        from nyc_world.simulation.relationships import RelationshipStore

        self.minds: dict[str, NPCMind] = {}
        self.relationships = relationships or RelationshipStore()
        self._tick = 0
        self._game_day = 1
        self._game_time = "08:00 AM"

    def register(self, mind: NPCMind) -> None:
        self.minds[mind.npc_id] = mind

    def get(self, npc_id: str) -> NPCMind | None:
        return self.minds.get(npc_id)

    def register_quest_npcs(self) -> None:
        self.register(create_maya_mind())
        self.register(create_alex_mind())

    def set_time_context(self, *, tick: int, game_day: int, game_time: str) -> None:
        self._tick = tick
        self._game_day = game_day
        self._game_time = game_time

    def on_player_helped(self, npc_id: str, quest_id: str) -> None:
        mind = self.get(npc_id)
        if not mind:
            return
        mind.remember("player_helped", self._tick, quest_id)
        self.relationships.record_fact(
            npc_id,
            "helped" if quest_id != "missing_camera" else "quest_complete",
            f"You helped with {quest_id.replace('_', ' ')}",
            tick=self._tick,
            game_day=self._game_day,
            game_time=self._game_time,
            target_id=quest_id,
            sentiment=0.8,
            trust_delta=15.0,
            friendship_delta=12.0,
        )
        mind.adjust_need(Need.SOCIAL, -0.2)
        mind.adjust_need(Need.MONEY, -0.1)
        mind.mood = min(1.0, mind.mood + 0.3)
        mind.goals = [g for g in mind.goals if g.id not in ("find_camera", "earn_rent")]

    def on_player_stole(self, npc_id: str, item_id: str) -> None:
        mind = self.get(npc_id)
        if not mind:
            return
        mind.remember("player_stole", self._tick, item_id)
        label = item_id.replace("_", " ")
        self.relationships.record_fact(
            npc_id,
            "stole",
            f"You stole her {label}",
            tick=self._tick,
            game_day=self._game_day,
            game_time=self._game_time,
            target_id=item_id,
            sentiment=-0.9,
            trust_delta=-25.0,
            friendship_delta=-15.0,
        )
        mind.mood = max(0.0, mind.mood - 0.4)

    def on_player_gave_money(self, npc_id: str, amount: int) -> None:
        mind = self.get(npc_id)
        self.relationships.record_fact(
            npc_id,
            "gave",
            f"You gave her ${amount}",
            tick=self._tick,
            game_day=self._game_day,
            game_time=self._game_time,
            amount=amount,
            sentiment=0.7,
            trust_delta=8.0,
            friendship_delta=6.0,
        )
        if mind:
            mind.adjust_need(Need.MONEY, -0.15)
            mind.mood = min(1.0, mind.mood + 0.15)

    def on_player_talked(self, npc_id: str) -> None:
        mind = self.get(npc_id)
        if mind:
            mind.remember("player_talked", self._tick)
            mind.adjust_need(Need.SOCIAL, -0.05)
        self.relationships.record_visit(
            npc_id,
            tick=self._tick,
            game_day=self._game_day,
            game_time=self._game_time,
        )
        rel = self.relationships.get(npc_id)
        if rel.visit_count > 1:
            rel.friendship = min(100.0, rel.friendship + 0.5)

    def on_quest_started(self, quest_id: str, giver_npc_id: str) -> None:
        mind = self.get(giver_npc_id)
        if mind and quest_id == "missing_camera":
            mind.goals = [
                Goal("find_camera", "Find her stolen camera", 0.95),
                Goal("work_cafe", "Work at the Village Cafe", 0.5),
            ]
        elif mind and quest_id == "maya_favor":
            mind.goals = [
                Goal("maya_favor", "Get help from a friend", 0.85),
                Goal("work_cafe", "Work at the Village Cafe", 0.5),
            ]

    def update(self, hour: int, minute: int, is_raining: bool, npc_positions: dict[str, tuple[float, float]]) -> None:
        self._tick += 1
        game_minutes = hour * 60 + minute

        for mind in self.minds.values():
            mind.adjust_need(Need.SOCIAL, 0.002)
            mind.adjust_need(Need.REST, 0.001)
            mind.adjust_need(Need.MONEY, 0.0015)

            if is_raining and mind.hates_rain:
                mind.mood = max(0.0, mind.mood - 0.01)
                mind.adjust_need(Need.COMFORT, 0.01)
                if mind.workplace_id:
                    mind.goals = [
                        Goal("seek_shelter", f"Stay dry at {mind.workplace_id}", 0.85),
                        *mind.goals,
                    ]
            elif not is_raining:
                mind.mood = min(1.0, mind.mood + 0.002)

            if game_minutes >= mind.home_hour * 60:
                mind.goals = [Goal("go_home", "Go home for the evening", 0.8), *mind.goals[:2]]

            seen: dict[str, Goal] = {}
            for goal in mind.goals:
                if goal.id not in seen or goal.priority > seen[goal.id].priority:
                    seen[goal.id] = goal
            mind.goals = sorted(seen.values(), key=lambda g: -g.priority)[:5]

            pos = npc_positions.get(mind.npc_id)
            if pos:
                for other_id, affinity in mind.npc_relationships.items():
                    if affinity < 0.3:
                        continue
                    other_pos = npc_positions.get(other_id)
                    if not other_pos:
                        continue
                    dx = pos[0] - other_pos[0]
                    dz = pos[1] - other_pos[1]
                    if dx * dx + dz * dz < 400:
                        mind.adjust_need(Need.SOCIAL, -0.005)

    def summary_for(self, npc_id: str) -> str | None:
        mind = self.get(npc_id)
        if not mind:
            return None
        rel = self.relationships.get(npc_id)
        parts = [
            f"{mind.display_name}: {mind.mood_label()}",
            f"goal={mind.current_goal_text()}",
            f"trust={int(rel.trust)}",
        ]
        if rel.has_fact("helped") or rel.has_fact("quest_complete"):
            parts.append("remembers you helped")
        if rel.has_fact("stole"):
            parts.append("remembers you stole")
        if rel.trust >= 60:
            parts.append("likes you")
        elif rel.trust <= 30:
            parts.append("wary")
        return " · ".join(parts)

    def memory_panel_lines(self, npc_id: str) -> list[str] | None:
        mind = self.get(npc_id)
        if not mind:
            return None
        rel = self.relationships.get(npc_id)
        last_seen = rel.last_seen_time or "just now"
        return format_memory_panel(
            mind.display_name,
            met_day=rel.met_day or self._game_day,
            met_time=rel.met_time or self._game_time,
            trust=rel.trust,
            friendship=rel.friendship,
            visit_count=rel.visit_count,
            last_seen=last_seen,
            facts=rel.facts,
            opinion=rel.opinion,
        )

    def to_dict(self) -> dict:
        return {npc_id: mind.to_dict() for npc_id, mind in self.minds.items()}

    def load_dict(self, data: dict) -> None:
        for npc_id, mind_data in data.items():
            self.minds[npc_id] = NPCMind.from_dict(mind_data)

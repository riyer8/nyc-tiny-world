"""NPC cognition — needs, goals, memory, and relationships."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Need(str, Enum):
    SOCIAL = "social"
    REST = "rest"
    WORK = "work"
    COMFORT = "comfort"


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
    player_affinity: float = 0.0
    mood: float = 0.5

    def __post_init__(self) -> None:
        if not self.needs:
            self.needs = {n.value: 0.5 for n in Need}

    def remember(self, event: str, tick: int, details: str = "") -> None:
        self.memories.append(Memory(event, tick, details))
        if len(self.memories) > 32:
            self.memories.pop(0)

    def has_memory(self, event: str) -> bool:
        return any(m.event == event for m in self.memories)

    def adjust_need(self, need: Need | str, delta: float) -> None:
        key = need.value if isinstance(need, Need) else need
        self.needs[key] = max(0.0, min(1.0, self.needs.get(key, 0.5) + delta))

    def adjust_player_affinity(self, delta: float) -> float:
        self.player_affinity = max(-1.0, min(1.0, self.player_affinity + delta))
        return self.player_affinity

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


def create_maya_mind() -> NPCMind:
    return NPCMind(
        npc_id="maya",
        display_name="Maya",
        workplace_id="cafe_village",
        home_hour=18,
        hates_rain=True,
        needs={Need.SOCIAL.value: 0.6, Need.WORK.value: 0.7, Need.REST.value: 0.4, Need.COMFORT.value: 0.5},
        goals=[
            Goal("work_cafe", "Work at the Village Cafe", 0.6),
            Goal("find_camera", "Find her stolen camera", 0.9),
        ],
        npc_relationships={"alex": 0.6},
    )


def create_alex_mind() -> NPCMind:
    return NPCMind(
        npc_id="alex",
        display_name="Alex",
        home_hour=22,
        hates_rain=False,
        needs={Need.SOCIAL.value: 0.5, Need.WORK.value: 0.3, Need.REST.value: 0.6, Need.COMFORT.value: 0.4},
        goals=[Goal("get_to_class", "Get to class on time", 0.7)],
        npc_relationships={"maya": 0.5},
    )


class NPCMindRegistry:
    """Maps NPC ids to cognitive profiles."""

    def __init__(self) -> None:
        self.minds: dict[str, NPCMind] = {}
        self._tick = 0

    def register(self, mind: NPCMind) -> None:
        self.minds[mind.npc_id] = mind

    def get(self, npc_id: str) -> NPCMind | None:
        return self.minds.get(npc_id)

    def register_quest_npcs(self) -> None:
        self.register(create_maya_mind())
        self.register(create_alex_mind())

    def on_player_helped(self, npc_id: str, quest_id: str) -> None:
        mind = self.get(npc_id)
        if not mind:
            return
        mind.remember("player_helped", self._tick, quest_id)
        mind.adjust_player_affinity(0.5)
        mind.adjust_need(Need.SOCIAL, -0.2)
        mind.mood = min(1.0, mind.mood + 0.3)
        mind.goals = [g for g in mind.goals if g.id != "find_camera"]

    def on_player_stole(self, npc_id: str, item_id: str) -> None:
        mind = self.get(npc_id)
        if not mind:
            return
        mind.remember("player_stole", self._tick, item_id)
        mind.adjust_player_affinity(-0.6)
        mind.mood = max(0.0, mind.mood - 0.4)

    def on_player_talked(self, npc_id: str) -> None:
        mind = self.get(npc_id)
        if not mind:
            return
        mind.remember("player_talked", self._tick)
        mind.adjust_need(Need.SOCIAL, -0.05)
        mind.adjust_player_affinity(0.02)

    def on_quest_started(self, quest_id: str, giver_npc_id: str) -> None:
        mind = self.get(giver_npc_id)
        if mind and quest_id == "missing_camera":
            mind.goals = [
                Goal("find_camera", "Find her stolen camera", 0.95),
                Goal("work_cafe", "Work at the Village Cafe", 0.5),
            ]

    def update(self, hour: int, minute: int, is_raining: bool, npc_positions: dict[str, tuple[float, float]]) -> None:
        self._tick += 1
        game_minutes = hour * 60 + minute

        for mind in self.minds.values():
            # Drift needs upward over time.
            mind.adjust_need(Need.SOCIAL, 0.002)
            mind.adjust_need(Need.REST, 0.001)

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

            # Go home after home_hour.
            if game_minutes >= mind.home_hour * 60:
                mind.goals = [Goal("go_home", "Go home for the evening", 0.8), *mind.goals[:2]]

            # Deduplicate goals by id, keep highest priority.
            seen: dict[str, Goal] = {}
            for goal in mind.goals:
                if goal.id not in seen or goal.priority > seen[goal.id].priority:
                    seen[goal.id] = goal
            mind.goals = sorted(seen.values(), key=lambda g: -g.priority)[:5]

            # NPC-to-NPC proximity boosts social need relief for friends.
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
                    if dx * dx + dz * dz < 400:  # within ~20m
                        mind.adjust_need(Need.SOCIAL, -0.005)

    def summary_for(self, npc_id: str) -> str | None:
        mind = self.get(npc_id)
        if not mind:
            return None
        parts = [
            f"{mind.display_name}: {mind.mood_label()}",
            f"goal={mind.current_goal_text()}",
        ]
        if mind.has_memory("player_helped"):
            parts.append("remembers you helped")
        if mind.has_memory("player_stole"):
            parts.append("remembers you stole")
        if mind.player_affinity >= 0.3:
            parts.append("likes you")
        elif mind.player_affinity <= -0.3:
            parts.append("dislikes you")
        return " · ".join(parts)

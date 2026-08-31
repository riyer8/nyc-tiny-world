"""Quest data types shared by quest system and procedural generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from nyc_world.game.profile import QuestReward


class QuestState(str, Enum):
    LOCKED = "locked"
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"


class ObjectiveType(str, Enum):
    TALK_NPC = "talk_npc"
    VISIT = "visit"
    ENTER_BUILDING = "enter_building"
    COLLECT = "collect"
    RETURN_TO = "return_to"


@dataclass
class QuestObjective:
    id: str
    description: str
    type: ObjectiveType
    target_id: str
    completed: bool = False


@dataclass
class Quest:
    id: str
    title: str
    emoji: str
    objectives: list[QuestObjective]
    state: QuestState = QuestState.AVAILABLE
    reward: QuestReward = field(default_factory=QuestReward)
    giver_npc_id: str = ""
    generated: bool = False
    intro_key: str = ""
    complete_key: str = ""

    @property
    def current_objective(self) -> QuestObjective | None:
        for obj in self.objectives:
            if not obj.completed:
                return obj
        return None

    def is_complete(self) -> bool:
        return all(o.completed for o in self.objectives)

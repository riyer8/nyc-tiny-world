"""Quest and adventure system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


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
    reward: str = ""
    giver_npc_id: str = ""

    @property
    def current_objective(self) -> QuestObjective | None:
        for obj in self.objectives:
            if not obj.completed:
                return obj
        return None

    def is_complete(self) -> bool:
        return all(o.completed for o in self.objectives)


DIALOGUE: dict[str, list[str]] = {
    "maya_intro": [
        "Maya: Hey! Someone stole my camera near the park.",
        "Maya: I need it back before my photo show tonight.",
        "Maya: Can you help me find it?",
    ],
    "maya_quest_accepted": [
        "Maya: Thank you! Start at the cafe on MacDougal.",
        "Maya: Someone there might have seen something.",
    ],
    "maya_no_camera": [
        "Maya: Any luck? Check the cafe, then follow the clues.",
    ],
    "maya_quest_complete": [
        "Maya: You found it! You're a lifesaver!",
        "Maya: Here's a coffee token for your trouble. ☕",
        "🎉 QUEST COMPLETE: The Missing Camera",
    ],
    "cafe_clue": [
        "Barista: Alex was here this morning, looked worried.",
        "Barista: Said something about the old library on 6th Avenue.",
    ],
    "alex_clue": [
        "Alex: I saw a camera near the library reading room.",
        "Alex: I didn't take it — honest! Check inside.",
    ],
    "alex_default": [
        "Alex: I'm late for class. Good luck finding that camera!",
    ],
    "found_camera": [
        "You pick up Maya's camera. It's still working!",
        "📷 Camera added to inventory.",
    ],
    "subway_ride": [
        "You swipe into the subway. The Uptown train rumbles below.",
        "(Fast travel coming soon — for now, explore on foot!)",
    ],
}


def create_missing_camera_quest() -> Quest:
    return Quest(
        id="missing_camera",
        title="The Missing Camera",
        emoji="🗽",
        giver_npc_id="maya",
        reward="coffee_token",
        objectives=[
            QuestObjective("talk_maya", "Talk to Maya in Washington Square", ObjectiveType.TALK_NPC, "maya"),
            QuestObjective("visit_cafe", "Visit the Village Cafe", ObjectiveType.VISIT, "cafe_village"),
            QuestObjective("talk_alex", "Talk to Alex for a clue", ObjectiveType.TALK_NPC, "alex"),
            QuestObjective("enter_library", "Enter the Jefferson Market Library", ObjectiveType.ENTER_BUILDING, "library_interior"),
            QuestObjective("collect_camera", "Find the camera inside", ObjectiveType.COLLECT, "camera"),
            QuestObjective("return_maya", "Return the camera to Maya", ObjectiveType.RETURN_TO, "maya"),
        ],
    )


class QuestManager:
    def __init__(self) -> None:
        self.quests: dict[str, Quest] = {
            "missing_camera": create_missing_camera_quest(),
        }
        self.active_quest_id: str | None = None
        self.completed_quests: set[str] = set()
        self.inventory: set[str] = set()

    @property
    def active_quest(self) -> Quest | None:
        if self.active_quest_id:
            return self.quests.get(self.active_quest_id)
        return None

    def start_quest(self, quest_id: str) -> list[str]:
        quest = self.quests.get(quest_id)
        if not quest or quest.state == QuestState.COMPLETED:
            return []
        quest.state = QuestState.ACTIVE
        self.active_quest_id = quest_id
        if quest_id == "missing_camera":
            return list(DIALOGUE["maya_quest_accepted"])
        return [f"Quest started: {quest.title}"]

    def on_talk_npc(self, npc_id: str) -> list[str]:
        lines: list[str] = []
        quest = self.active_quest

        if not quest and npc_id == "maya":
            lines.extend(DIALOGUE["maya_intro"])
            lines.extend(self.start_quest("missing_camera"))
            quest = self.active_quest
            if quest:
                obj = quest.current_objective
                if obj and obj.type == ObjectiveType.TALK_NPC and obj.target_id == "maya":
                    self._complete_objective(obj)
            return lines

        if not quest:
            return lines

        obj = quest.current_objective
        if quest.id == "missing_camera":
            if npc_id == "maya":
                if obj and obj.type == ObjectiveType.RETURN_TO and obj.target_id == "maya":
                    if "camera" in self.inventory:
                        self._complete_objective(obj)
                        quest.state = QuestState.COMPLETED
                        self.completed_quests.add(quest.id)
                        self.active_quest_id = None
                        self.inventory.discard("camera")
                        lines.extend(DIALOGUE["maya_quest_complete"])
                    else:
                        lines.extend(DIALOGUE["maya_no_camera"])
                elif obj and obj.type == ObjectiveType.TALK_NPC and obj.target_id == "maya":
                    self._complete_objective(obj)
                    lines.extend(DIALOGUE["maya_quest_accepted"])
                else:
                    lines.extend(DIALOGUE["maya_no_camera"])
            elif npc_id == "alex":
                if obj and obj.type == ObjectiveType.TALK_NPC and obj.target_id == "alex":
                    self._complete_objective(obj)
                    lines.extend(DIALOGUE["alex_clue"])
                else:
                    lines.extend(DIALOGUE["alex_default"])
        return lines

    def on_visit(self, interactable_id: str) -> list[str]:
        lines: list[str] = []
        quest = self.active_quest
        if not quest:
            return lines
        obj = quest.current_objective
        if not obj or obj.type != ObjectiveType.VISIT:
            return lines
        if obj.target_id == interactable_id:
            self._complete_objective(obj)
            if interactable_id == "cafe_village":
                lines.extend(DIALOGUE["cafe_clue"])
        return lines

    def on_enter_building(self, interior_id: str) -> list[str]:
        quest = self.active_quest
        if not quest:
            return []
        obj = quest.current_objective
        if obj and obj.type == ObjectiveType.ENTER_BUILDING and obj.target_id == interior_id:
            self._complete_objective(obj)
            return [f"You enter {interior_id.replace('_', ' ').title()}."]
        return []

    def on_collect(self, item_id: str) -> list[str]:
        lines: list[str] = []
        quest = self.active_quest
        if not quest:
            return lines
        obj = quest.current_objective
        if obj and obj.type == ObjectiveType.COLLECT and obj.target_id == item_id:
            self.inventory.add(item_id)
            self._complete_objective(obj)
            lines.extend(DIALOGUE.get("found_camera", [f"Picked up {item_id}."]))
        return lines

    def _complete_objective(self, obj: QuestObjective) -> None:
        obj.completed = True

    def hud_objective_text(self) -> str | None:
        quest = self.active_quest
        if not quest:
            return None
        obj = quest.current_objective
        if obj:
            return f"{quest.emoji} {quest.title}: {obj.description}"
        return f"{quest.emoji} {quest.title}: Complete!"

"""Quest and adventure system."""

from __future__ import annotations

from nyc_world.game.dialogue import lines_for_key, pick_npc_greeting
from nyc_world.game.dialogue_lines import DIALOGUE
from nyc_world.game.items import item_display
from nyc_world.game.profile import PlayerProfile, QuestReward
from nyc_world.game.quest_types import ObjectiveType, Quest, QuestObjective, QuestState
from nyc_world.simulation.quest_gen import QuestGenContext, scan_generated_quests


# Re-export for backward compatibility.
__all__ = [
    "DIALOGUE",
    "ObjectiveType",
    "Quest",
    "QuestManager",
    "QuestObjective",
    "QuestState",
    "create_missing_camera_quest",
]




def create_missing_camera_quest() -> Quest:
    return Quest(
        id="missing_camera",
        title="The Missing Camera",
        emoji="🗽",
        giver_npc_id="maya",
        reward=QuestReward(
            xp=75,
            money=15,
            items={"coffee": 1, "coffee_token": 1},
            relationship_changes={"maya": 0.5},
        ),
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
    def __init__(self, player: PlayerProfile | None = None, minds=None) -> None:
        self.player = player or PlayerProfile()
        self.minds = minds
        self.quests: dict[str, Quest] = {
            "missing_camera": create_missing_camera_quest(),
        }
        self.active_quest_id: str | None = None
        self._tick = 0
        self._game_day = 1
        self._agents = None

    def set_agents(self, agents) -> None:
        self._agents = agents

    def set_time_context(self, *, tick: int, game_day: int) -> None:
        self._tick = tick
        self._game_day = game_day

    def refresh_generated_quests(self) -> None:
        """Add procedural quests when NPC needs warrant it."""
        if not self.minds:
            return
        if "missing_camera" not in self.completed_quests:
            return
        ctx = QuestGenContext(game_day=self._game_day, tick=self._tick)
        for generated in scan_generated_quests(
            self.minds,
            self._agents,
            ctx,
            completed_quests=self.completed_quests,
            active_quest_id=self.active_quest_id,
            prerequisite_completed=self.completed_quests,
        ):
            if generated.id not in self.quests:
                self.quests[generated.id] = generated

    def _available_generated_for(self, npc_id: str) -> Quest | None:
        for quest in self.quests.values():
            if quest.generated and quest.giver_npc_id == npc_id and quest.state == QuestState.AVAILABLE:
                return quest
        return None

    @property
    def completed_quests(self) -> set[str]:
        return set(self.player.quests_completed)

    @property
    def active_quest(self) -> Quest | None:
        if self.active_quest_id:
            return self.quests.get(self.active_quest_id)
        return None

    def has_item(self, item_id: str) -> bool:
        return self.player.has_item(item_id)

    def start_quest(self, quest_id: str) -> list[str]:
        quest = self.quests.get(quest_id)
        if not quest or quest.state == QuestState.COMPLETED:
            return []
        quest.state = QuestState.ACTIVE
        self.active_quest_id = quest_id
        if self.minds:
            self.minds.on_quest_started(quest_id, quest.giver_npc_id)
        if quest_id == "missing_camera":
            return list(DIALOGUE["maya_quest_accepted"])
        return [f"Quest started: {quest.title}"]

    def _complete_quest(self, quest: Quest) -> list[str]:
        quest.state = QuestState.COMPLETED
        self.active_quest_id = None
        self.player.complete_quest(quest.id)
        lines: list[str] = []
        if not quest.reward.is_empty():
            lines.extend(self.player.apply_reward(quest.reward))
        if self.minds and quest.giver_npc_id:
            self.minds.on_player_helped(quest.giver_npc_id, quest.id)
            self.minds.relationships.sync_to_profile(self.player)
        return lines

    def on_talk_npc(self, npc_id: str) -> list[str]:
        lines: list[str] = []
        if self.minds:
            self.minds.on_player_talked(npc_id)

        quest = self.active_quest
        if quest:
            return self._handle_active_quest_talk(npc_id, quest, lines)

        if npc_id == "maya":
            if "missing_camera" not in self.completed_quests:
                lines.extend(DIALOGUE["maya_intro"])
                lines.extend(self.start_quest("missing_camera"))
                quest = self.active_quest
                if quest:
                    obj = quest.current_objective
                    if obj and obj.type == ObjectiveType.TALK_NPC and obj.target_id == "maya":
                        self._complete_objective(obj)
                return lines

            self.refresh_generated_quests()
            offered = self._available_generated_for(npc_id)
            if offered:
                if offered.intro_key:
                    lines.extend(lines_for_key(offered.intro_key))
                lines.extend(self.start_quest(offered.id))
                obj = offered.current_objective
                if obj and obj.type == ObjectiveType.TALK_NPC and obj.target_id == npc_id:
                    self._complete_objective(obj)
                return lines

        if "missing_camera" in self.completed_quests:
            self.refresh_generated_quests()
            offered = self._available_generated_for(npc_id)
            if offered:
                if offered.intro_key:
                    lines.extend(lines_for_key(offered.intro_key))
                lines.extend(self.start_quest(offered.id))
                return lines

        if self.minds:
            rel = self.minds.relationships.get(npc_id)
            greeting_key = pick_npc_greeting(
                npc_id,
                rel,
                quest_active_id=None,
                quest_completed=self.completed_quests,
                minds=self.minds,
            )
            if greeting_key:
                lines.extend(lines_for_key(greeting_key))
        return lines

    def _handle_active_quest_talk(self, npc_id: str, quest: Quest, lines: list[str]) -> list[str]:
        if quest.id == "missing_camera":
            return self._handle_missing_camera_talk(npc_id, quest, lines)
        if quest.generated:
            return self._handle_generated_quest_talk(npc_id, quest, lines)
        if quest.id == "maya_favor":
            return self._handle_generated_quest_talk(npc_id, quest, lines)
        return lines

    def _handle_missing_camera_talk(self, npc_id: str, quest: Quest, lines: list[str]) -> list[str]:
        obj = quest.current_objective
        if npc_id == "maya":
            if obj and obj.type == ObjectiveType.RETURN_TO and obj.target_id == "maya":
                if self.has_item("camera"):
                    self._complete_objective(obj)
                    lines.extend(DIALOGUE["maya_quest_complete"])
                    lines.extend(self._complete_quest(quest))
                    self.player.remove_item("camera")
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
                self.player.adjust_relationship("alex", 0.1)
                lines.extend(DIALOGUE["alex_clue"])
            else:
                lines.extend(DIALOGUE["alex_default"])
        return lines

    def _handle_generated_quest_talk(self, npc_id: str, quest: Quest, lines: list[str]) -> list[str]:
        obj = quest.current_objective
        if not obj:
            return lines

        if obj.type == ObjectiveType.TALK_NPC and obj.target_id == npc_id:
            if obj is quest.objectives[0] and quest.intro_key:
                lines.extend(lines_for_key(quest.intro_key))
            if quest.id.endswith("_delivery") and npc_id == "maya":
                if not self.has_item("coffee_bag"):
                    lines.append("Maya: Where's the coffee Alex promised?")
                    return lines
                self.player.remove_item("coffee_bag")
            self._complete_objective(obj)
            if quest.is_complete():
                if quest.complete_key:
                    lines.extend(lines_for_key(quest.complete_key))
                lines.extend(self._complete_quest(quest))
            return lines

        if obj.type == ObjectiveType.RETURN_TO and obj.target_id == npc_id:
            required = {
                "alex_note": "alex_note",
                "library_clue": "library_clue",
            }
            for item_id, need in required.items():
                if obj.target_id == quest.giver_npc_id and quest.objectives[-2].target_id == item_id:
                    if not self.has_item(need):
                        lines.append(f"{npc_id.title()}: You don't have what I need yet.")
                        return lines
                    self.player.remove_item(need)
            self._complete_objective(obj)
            if quest.complete_key:
                lines.extend(lines_for_key(quest.complete_key))
            lines.extend(self._complete_quest(quest))
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
            self.player.add_item(item_id)
            self._complete_objective(obj)
            if item_id == "alex_note":
                lines.extend(DIALOGUE.get("found_alex_note", [f"Picked up {item_id}."]))
            elif item_id == "coffee_bag":
                lines.extend(DIALOGUE.get("found_coffee_bag", [f"Picked up {item_id}."]))
            elif item_id == "library_clue":
                lines.extend(DIALOGUE.get("found_library_clue", [f"Picked up {item_id}."]))
            else:
                lines.extend(DIALOGUE.get("found_camera", [f"Picked up {item_id}."]))
            lines.append(f"{item_display(item_id)} added to inventory.")
        return lines

    def _complete_objective(self, obj: QuestObjective) -> None:
        obj.completed = True

    def hud_objective_text(self) -> str | None:
        quest = self.active_quest
        if not quest:
            if self.completed_quests:
                return f"✓ {len(self.completed_quests)} quest(s) completed"
            return None
        obj = quest.current_objective
        if obj:
            return f"{quest.emoji} {quest.title}: {obj.description}"
        return f"{quest.emoji} {quest.title}: Complete!"

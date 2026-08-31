"""Procedural quest generation from NPC needs, agent brains, and social graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from nyc_world.game.profile import QuestReward
from nyc_world.game.quest_types import ObjectiveType, Quest, QuestObjective, QuestState
from nyc_world.simulation.agent import AgentBrain, AgentController
from nyc_world.simulation.npc_mind import NPCMind, NPCMindRegistry


@dataclass
class QuestGenContext:
    game_day: int
    tick: int
    landmark_ids: list[str] = field(default_factory=list)


@dataclass
class QuestTemplate:
    template_id: str
    emoji: str
    title: str
    intro_key: str
    complete_key: str
    builder: Callable[..., Quest | None]

    def try_build(
        self,
        giver_id: str,
        mind: NPCMind | None,
        brain: AgentBrain | None,
        ctx: QuestGenContext,
        *,
        completed: set[str],
        active_id: str | None,
    ) -> Quest | None:
        if active_id:
            return None
        quest_id = f"{giver_id}_{self.template_id}"
        if quest_id in completed:
            return None
        return self.builder(giver_id, mind, brain, ctx, quest_id=quest_id, template=self)


def _fetch_favor_quest(
    giver_id: str,
    mind: NPCMind | None,
    brain: AgentBrain | None,
    ctx: QuestGenContext,
    *,
    quest_id: str,
    template: QuestTemplate,
) -> Quest | None:
    if giver_id != "maya" or not mind:
        return None
    money_need = brain.needs.money if brain else mind.needs.get("money", 0.5)
    if money_need < 0.65:
        return None
    return Quest(
        id=quest_id,
        title=template.title,
        emoji=template.emoji,
        giver_npc_id=giver_id,
        state=QuestState.AVAILABLE,
        generated=True,
        intro_key=template.intro_key,
        complete_key=template.complete_key,
        reward=QuestReward(xp=40, items={"coffee_token": 1}, relationship_changes={"maya": 0.35}),
        objectives=[
            QuestObjective("talk", f"Talk to {giver_id.title()}", ObjectiveType.TALK_NPC, giver_id),
            QuestObjective("library", "Check the Jefferson Market Library", ObjectiveType.ENTER_BUILDING, "library_interior"),
            QuestObjective("note", "Find Alex's note in the library", ObjectiveType.COLLECT, "alex_note"),
            QuestObjective("return", f"Return to {giver_id.title()}", ObjectiveType.RETURN_TO, giver_id),
        ],
    )


def _deliver_coffee_quest(
    giver_id: str,
    mind: NPCMind | None,
    brain: AgentBrain | None,
    ctx: QuestGenContext,
    *,
    quest_id: str,
    template: QuestTemplate,
) -> Quest | None:
    if giver_id != "alex" or not brain:
        return None
    if brain.needs.social < 0.55:
        return None
    if "maya" not in (mind.npc_relationships if mind else {}):
        return None
    return Quest(
        id=quest_id,
        title=template.title,
        emoji=template.emoji,
        giver_npc_id=giver_id,
        state=QuestState.AVAILABLE,
        generated=True,
        intro_key=template.intro_key,
        complete_key=template.complete_key,
        reward=QuestReward(xp=30, money=10, relationship_changes={"alex": 0.25, "maya": 0.15}),
        objectives=[
            QuestObjective("talk", "Talk to Alex", ObjectiveType.TALK_NPC, "alex"),
            QuestObjective("cafe", "Pick up coffee at the Village Cafe", ObjectiveType.VISIT, "cafe_village"),
            QuestObjective("collect", "Grab the coffee bag", ObjectiveType.COLLECT, "coffee_bag"),
            QuestObjective("deliver", "Bring it to Maya", ObjectiveType.TALK_NPC, "maya"),
        ],
    )


def _investigate_library_quest(
    giver_id: str,
    mind: NPCMind | None,
    brain: AgentBrain | None,
    ctx: QuestGenContext,
    *,
    quest_id: str,
    template: QuestTemplate,
) -> Quest | None:
    if not brain or brain.personality.curiosity < 0.6:
        return None
    if giver_id not in ("alex", "maya"):
        return None
    return Quest(
        id=quest_id,
        title=template.title,
        emoji=template.emoji,
        giver_npc_id=giver_id,
        state=QuestState.AVAILABLE,
        generated=True,
        intro_key=template.intro_key,
        complete_key=template.complete_key,
        reward=QuestReward(xp=35, relationship_changes={giver_id: 0.2}),
        objectives=[
            QuestObjective("talk", f"Talk to {giver_id.title()}", ObjectiveType.TALK_NPC, giver_id),
            QuestObjective("enter", "Search the library", ObjectiveType.ENTER_BUILDING, "library_interior"),
            QuestObjective("find", "Look for clues inside", ObjectiveType.COLLECT, "library_clue"),
            QuestObjective("report", f"Report back to {giver_id.title()}", ObjectiveType.RETURN_TO, giver_id),
        ],
    )


QUEST_TEMPLATES: list[QuestTemplate] = [
    QuestTemplate("favor", "📷", "A Favor for Maya", "maya_favor_intro", "maya_favor_complete", _fetch_favor_quest),
    QuestTemplate("delivery", "☕", "Coffee for Maya", "alex_delivery_intro", "alex_delivery_complete", _deliver_coffee_quest),
    QuestTemplate("investigate", "🔍", "Strange Noises at the Library", "investigate_intro", "investigate_complete", _investigate_library_quest),
]


def scan_generated_quests(
    minds: NPCMindRegistry,
    agents: AgentController | None,
    ctx: QuestGenContext,
    *,
    completed_quests: set[str],
    active_quest_id: str | None,
    prerequisite_completed: set[str] | None = None,
) -> list[Quest]:
    """Scan NPCs and return quests that match template preconditions."""
    if prerequisite_completed and "missing_camera" not in prerequisite_completed:
        return []

    results: list[Quest] = []
    giver_ids = ["maya", "alex"]
    if agents:
        for npc_id in list(agents.brains.keys())[:8]:
            if npc_id not in giver_ids:
                giver_ids.append(npc_id)

    for giver_id in giver_ids:
        mind = minds.get(giver_id)
        brain = agents.get(giver_id) if agents else None
        for template in QUEST_TEMPLATES:
            quest = template.try_build(
                giver_id,
                mind,
                brain,
                ctx,
                completed=completed_quests,
                active_id=active_quest_id,
            )
            if quest and quest.id not in {q.id for q in results}:
                results.append(quest)
    return results


def try_generate_maya_favor(
    minds: NPCMindRegistry,
    ctx: QuestGenContext,
    *,
    completed_quests: set[str],
    active_quest_id: str | None,
) -> Quest | None:
    """Backward-compatible wrapper."""
    quests = scan_generated_quests(
        minds,
        None,
        ctx,
        completed_quests=completed_quests,
        active_quest_id=active_quest_id,
        prerequisite_completed=completed_quests,
    )
    for q in quests:
        if q.giver_npc_id == "maya" and q.id.endswith("_favor"):
            return q
    return None

"""Tag-based NPC dialogue routing driven by memory and quest state."""

from __future__ import annotations

from nyc_world.game.dialogue_lines import DIALOGUE
from nyc_world.simulation.relationships import NPCPlayerRelationship


def pick_npc_greeting(
    npc_id: str,
    rel: NPCPlayerRelationship,
    *,
    quest_active_id: str | None,
    quest_completed: set[str],
    minds=None,
) -> str | None:
    """Return a dialogue key for the NPC greeting, or None to fall through to quest logic."""
    if rel.has_fact("stole"):
        key = f"{npc_id}_hostile"
        if key in DIALOGUE:
            return key
        return "npc_hostile_generic"

    if rel.visit_count >= 2 and rel.trust >= 55 and rel.friendship >= 40:
        key = f"{npc_id}_hoping_you_come_by"
        if key in DIALOGUE:
            return key

    if npc_id == "maya" and minds and minds.get("maya"):
        maya = minds.get("maya")
        if maya and any(m.event == "new_coworker" for m in maya.memories):
            return "maya_new_coworker"

    if quest_active_id is None and f"missing_camera" in quest_completed and npc_id == "maya":
        if rel.trust >= 60:
            return "maya_friendly"
        return "maya_friendly"

    if rel.visit_count == 0 and npc_id == "maya" and "missing_camera" not in quest_completed:
        return None  # quest intro handled by QuestManager

    if rel.visit_count >= 1:
        key = f"{npc_id}_returning"
        if key in DIALOGUE:
            return key

    for pack_key, _lines in DIALOGUE.items():
        if pack_key == npc_id or pack_key.startswith(f"{npc_id}_"):
            return pack_key

    return None


def lines_for_key(key: str) -> list[str]:
    return list(DIALOGUE.get(key, []))

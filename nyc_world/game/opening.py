"""First-run beat — Maya is mid-conversation when the city appears."""

from __future__ import annotations

import math

from nyc_world.game.dialogue_lines import DIALOGUE


def look_yaw_toward(px: float, pz: float, tx: float, tz: float) -> float:
    """Camera yaw that faces the player toward (tx, tz)."""
    return math.atan2(tx - px, -(tz - pz))


def apply_opening_beat(session, px: float, pz: float, yaw: float) -> float:
    """Face Maya and start her camera plea. Skip if a save was loaded."""
    if getattr(session, "_loaded_position", None):
        return yaw
    if "missing_camera" in session.player.quests_completed:
        return yaw

    maya = next((npc for npc in session.city.npcs if npc.name == "maya"), None)
    if maya is None:
        return yaw

    session.hud.dialogue_lines = list(DIALOGUE["maya_intro"])
    session.hud.prompt = "E — Help Maya find her camera"
    session.hud.quest_text = session.quests.hud_objective_text() or "📷 The Missing Camera: Talk to Maya"
    return look_yaw_toward(px, pz, maya.x, maya.z)


def quest_marker_ids(session) -> list[str]:
    if "missing_camera" in session.player.quests_completed:
        return []
    return ["maya"]

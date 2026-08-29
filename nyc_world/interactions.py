"""Backward-compatible import path. Prefer: from nyc_world.game.interactions import ..."""

from nyc_world.game.interactions import (
    InteractionResult,
    InteractionSystem,
    assign_quest_npcs,
    build_world_interactables,
)

__all__ = [
    "InteractionResult",
    "InteractionSystem",
    "assign_quest_npcs",
    "build_world_interactables",
]

"""Backward-compatible import path. Prefer: from nyc_world.game.interactables import ..."""

from nyc_world.game.interactables import Interactable, InteractableKind

__all__ = ["Interactable", "InteractableKind"]

"""Backward-compatible import path. Prefer: from nyc_world.game import GameSession."""

from nyc_world.game.game_session import GameSession, HudState, INTERIOR_SPAWN

__all__ = ["GameSession", "HudState", "INTERIOR_SPAWN"]

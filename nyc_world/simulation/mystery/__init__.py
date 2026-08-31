"""Procedural mystery generation and investigation."""

from nyc_world.simulation.mystery.case import MysteryCase, MysteryInvestigation
from nyc_world.simulation.mystery.gen import generate_mystery
from nyc_world.simulation.mystery.investigation import (
    discover_clues_at_location,
    discover_clues_from_npc,
    investigation_hud_lines,
)

__all__ = [
    "MysteryCase",
    "MysteryInvestigation",
    "generate_mystery",
    "discover_clues_at_location",
    "discover_clues_from_npc",
    "investigation_hud_lines",
]

"""Interactable entities in the world."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class InteractableKind(str, Enum):
    SUBWAY = "subway"
    CAFE = "cafe"
    BUILDING = "building"
    NPC = "npc"
    OBJECT = "object"


@dataclass
class Interactable:
    id: str
    kind: InteractableKind
    x: float
    z: float
    label: str
    radius: float = 3.5
    interior_id: str | None = None
    dialogue_id: str | None = None
    item_id: str | None = None
    quest_npc: bool = False
    emoji: str = ""

    def distance_to(self, x: float, z: float) -> float:
        dx, dz = self.x - x, self.z - z
        return (dx * dx + dz * dz) ** 0.5

    def prompt_text(self) -> str:
        icon = self.emoji or _default_emoji(self.kind)
        action = _default_action(self.kind, self.interior_id)
        return f"{icon}\n{self.label.upper()}\n\n[ E ]\n{action}"


def _default_emoji(kind: InteractableKind) -> str:
    return {
        InteractableKind.SUBWAY: "🚇",
        InteractableKind.CAFE: "☕",
        InteractableKind.BUILDING: "🏢",
        InteractableKind.NPC: "🧑",
        InteractableKind.OBJECT: "📦",
    }[kind]


def _default_action(kind: InteractableKind, interior_id: str | None) -> str:
    if kind == InteractableKind.CAFE:
        return "ENTER"
    if kind == InteractableKind.BUILDING and interior_id:
        return "ENTER"
    if kind == InteractableKind.NPC:
        return "TALK"
    if kind == InteractableKind.OBJECT:
        return "PICK UP"
    if kind == InteractableKind.SUBWAY:
        return "ENTER"
    return "INTERACT"

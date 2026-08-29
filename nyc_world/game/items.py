"""Item catalog — ids, display names, and emojis."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ItemDef:
    id: str
    name: str
    emoji: str = ""
    description: str = ""

    def display(self, count: int = 1) -> str:
        label = f"{self.emoji} {self.name}".strip() if self.emoji else self.name
        if count > 1:
            return f"{label} ×{count}"
        return label


ITEMS: dict[str, ItemDef] = {
    "metro_card": ItemDef("metro_card", "MetroCard", "🎫", "Swipe for the subway."),
    "camera": ItemDef("camera", "Camera", "📷", "Maya's missing camera."),
    "coffee": ItemDef("coffee", "Coffee", "☕", "A hot cup from the Village Cafe."),
    "coffee_token": ItemDef("coffee_token", "Coffee Token", "🎟️", "Redeem for a free drink."),
    "mysterious_key": ItemDef("mysterious_key", "Mysterious Key", "🗝️", "An old brass key. No label."),
}


NPC_NAMES: dict[str, str] = {
    "maya": "Maya",
    "alex": "Alex",
}


def item_display(item_id: str, count: int = 1) -> str:
    """Human-readable inventory line for an item id."""
    item = ITEMS.get(item_id)
    if item:
        return item.display(count)
    return f"{item_id} ×{count}" if count > 1 else item_id

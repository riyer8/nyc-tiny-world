"""Player profile — inventory, XP, money, and relationships."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.game.items import NPC_NAMES, item_display

# XP thresholds for each level (level 1 starts at 0 XP).
LEVEL_XP: tuple[int, ...] = (0, 100, 250, 500, 1000, 2000, 4000)


@dataclass
class QuestReward:
    xp: int = 0
    money: int = 0
    items: dict[str, int] = field(default_factory=dict)
    relationship_changes: dict[str, float] = field(default_factory=dict)

    def is_empty(self) -> bool:
        return (
            self.xp == 0
            and self.money == 0
            and not self.items
            and not self.relationship_changes
        )


@dataclass
class PlayerProfile:
    money: int = 37
    xp: int = 0
    items: dict[str, int] = field(default_factory=lambda: {"metro_card": 1})
    quests_completed: list[str] = field(default_factory=list)
    relationships: dict[str, float] = field(default_factory=dict)

    # --- inventory ---------------------------------------------------------

    def has_item(self, item_id: str) -> bool:
        return self.items.get(item_id, 0) > 0

    def item_count(self, item_id: str) -> int:
        return self.items.get(item_id, 0)

    def add_item(self, item_id: str, count: int = 1) -> None:
        if count <= 0:
            return
        self.items[item_id] = self.items.get(item_id, 0) + count

    def remove_item(self, item_id: str, count: int = 1) -> bool:
        current = self.items.get(item_id, 0)
        if current < count:
            return False
        remaining = current - count
        if remaining == 0:
            del self.items[item_id]
        else:
            self.items[item_id] = remaining
        return True

    # --- progression -------------------------------------------------------

    @property
    def level(self) -> int:
        lvl = 1
        for threshold in LEVEL_XP[1:]:
            if self.xp >= threshold:
                lvl += 1
            else:
                break
        return lvl

    @property
    def xp_for_current_level(self) -> int:
        idx = min(self.level - 1, len(LEVEL_XP) - 1)
        return LEVEL_XP[idx]

    @property
    def xp_for_next_level(self) -> int | None:
        idx = self.level
        if idx >= len(LEVEL_XP):
            return None
        return LEVEL_XP[idx]

    @property
    def xp_to_next_level(self) -> int | None:
        nxt = self.xp_for_next_level
        if nxt is None:
            return None
        return max(0, nxt - self.xp)

    def add_xp(self, amount: int) -> list[str]:
        if amount <= 0:
            return []
        old_level = self.level
        self.xp += amount
        lines = [f"+{amount} XP"]
        if self.level > old_level:
            lines.append(f"⬆ Level {self.level}!")
        return lines

    def add_money(self, amount: int) -> list[str]:
        if amount == 0:
            return []
        self.money += amount
        sign = "+" if amount > 0 else ""
        return [f"{sign}${amount}"]

    def complete_quest(self, quest_id: str) -> None:
        if quest_id not in self.quests_completed:
            self.quests_completed.append(quest_id)

    # --- relationships -----------------------------------------------------

    def get_relationship(self, npc_id: str) -> float:
        return self.relationships.get(npc_id, 0.0)

    def adjust_relationship(self, npc_id: str, delta: float) -> float:
        value = max(-1.0, min(1.0, self.get_relationship(npc_id) + delta))
        self.relationships[npc_id] = value
        return value

    def relationship_label(self, npc_id: str) -> str:
        name = NPC_NAMES.get(npc_id, npc_id.title())
        value = self.get_relationship(npc_id)
        if value >= 0.75:
            tone = "adores you"
        elif value >= 0.4:
            tone = "likes you"
        elif value >= 0.15:
            tone = "warms up"
        elif value > -0.15:
            tone = "neutral"
        elif value > -0.4:
            tone = "is wary"
        else:
            tone = "dislikes you"
        pct = int(round(value * 100))
        sign = "+" if pct > 0 else ""
        return f"{name} {tone} ({sign}{pct}%)"

    # --- rewards -----------------------------------------------------------

    def apply_reward(self, reward: QuestReward) -> list[str]:
        lines: list[str] = []
        lines.extend(self.add_xp(reward.xp))
        lines.extend(self.add_money(reward.money))
        for item_id, count in reward.items.items():
            self.add_item(item_id, count)
            lines.append(f"{item_display(item_id, count)} added")
        for npc_id, delta in reward.relationship_changes.items():
            self.adjust_relationship(npc_id, delta)
            lines.append(self.relationship_label(npc_id))
        return lines

    # --- display / serialization -------------------------------------------

    def inventory_lines(self) -> list[str]:
        if not self.items:
            return ["  (empty)"]
        lines: list[str] = []
        for item_id in sorted(self.items):
            lines.append(f"  {item_display(item_id, self.items[item_id])}")
        return lines

    def profile_lines(self) -> list[str]:
        """Compact HUD block: level, money, inventory, relationships."""
        lines = [
            f"Level {self.level}  ·  {self.xp} XP",
            f"${self.money}",
            "🎒 Inventory",
            *self.inventory_lines(),
        ]
        if self.quests_completed:
            lines.append(f"✓ {len(self.quests_completed)} quest(s) done")
        notable = [
            (npc_id, value)
            for npc_id, value in self.relationships.items()
            if abs(value) >= 0.1
        ]
        if notable:
            lines.append("Relationships")
            for npc_id, _ in sorted(notable, key=lambda pair: -abs(pair[1])):
                lines.append(f"  {self.relationship_label(npc_id)}")
        return lines

    def to_dict(self) -> dict:
        return {
            "money": self.money,
            "xp": self.xp,
            "items": dict(self.items),
            "quests_completed": list(self.quests_completed),
            "relationships": dict(self.relationships),
        }

    @classmethod
    def from_dict(cls, data: dict) -> PlayerProfile:
        return cls(
            money=data.get("money", 37),
            xp=data.get("xp", 0),
            items=dict(data.get("items", {"metro_card": 1})),
            quests_completed=list(data.get("quests_completed", [])),
            relationships=dict(data.get("relationships", {})),
        )

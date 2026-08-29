"""Player and world actions for simulation steps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass
class PlayerMoveAction:
    dx: float = 0.0
    dz: float = 0.0
    sprint: bool = False
    jump: bool = False

    def to_dict(self) -> dict:
        return {"type": "move", "dx": self.dx, "dz": self.dz, "sprint": self.sprint, "jump": self.jump}

    @classmethod
    def from_dict(cls, data: dict) -> PlayerMoveAction:
        return cls(
            dx=data.get("dx", 0.0),
            dz=data.get("dz", 0.0),
            sprint=data.get("sprint", False),
            jump=data.get("jump", False),
        )


@dataclass
class InteractAction:
    target_id: str = ""

    def to_dict(self) -> dict:
        return {"type": "interact", "target_id": self.target_id}

    @classmethod
    def from_dict(cls, data: dict) -> InteractAction:
        return cls(target_id=data.get("target_id", ""))


@dataclass
class WaitAction:
    def to_dict(self) -> dict:
        return {"type": "wait"}

    @classmethod
    def from_dict(cls, data: dict) -> WaitAction:
        return cls()


Action = Union[PlayerMoveAction, InteractAction, WaitAction]


def action_from_dict(data: dict) -> Action:
    kind = data.get("type", "wait")
    if kind == "move":
        return PlayerMoveAction.from_dict(data)
    if kind == "interact":
        return InteractAction.from_dict(data)
    return WaitAction.from_dict(data)

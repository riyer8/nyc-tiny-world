"""Player avatar — visible character with walk animation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class PlayerAvatar:
    """Tracks walk cycle phase for leg/arm swing."""

    walk_phase: float = 0.0
    jacket: tuple[float, float, float] = (0.32, 0.52, 0.88)
    pants: tuple[float, float, float] = (0.22, 0.24, 0.32)

    def update(self, dt: float, *, moving: bool, sprinting: bool) -> None:
        if not moving:
            # Ease back toward idle stance.
            self.walk_phase *= max(0.0, 1.0 - dt * 8.0)
            return
        speed = 9.0 if sprinting else 5.5
        self.walk_phase += dt * speed

    @property
    def leg_swing(self) -> float:
        return math.sin(self.walk_phase) * 0.28

    @property
    def arm_swing(self) -> float:
        return math.sin(self.walk_phase + math.pi) * 0.22

    @property
    def bob(self) -> float:
        return abs(math.sin(self.walk_phase * 2.0)) * 0.04

"""Player avatar — visible character with walk animation."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


def camera_facing_yaw(camera_yaw: float) -> float:
    """Convert third-person camera yaw to mesh heading (matches NPCs/vehicles)."""
    return math.atan2(math.sin(camera_yaw), -math.cos(camera_yaw))


def _lerp_angle(current: float, target: float, t: float) -> float:
    delta = math.atan2(math.sin(target - current), math.cos(target - current))
    return current + delta * t


@dataclass
class PlayerAvatar:
    """Tracks walk cycle phase for leg/arm swing."""

    walk_phase: float = 0.0
    facing_yaw: float = 0.0
    jacket: tuple[float, float, float] = (0.32, 0.52, 0.88)
    pants: tuple[float, float, float] = (0.22, 0.24, 0.32)

    def update(
        self,
        dt: float,
        *,
        moving: bool,
        sprinting: bool,
        move_x: float = 0.0,
        move_z: float = 0.0,
        camera_yaw: float = 0.0,
    ) -> None:
        target_yaw = camera_facing_yaw(camera_yaw)
        if moving and (move_x or move_z):
            target_yaw = math.atan2(move_x, move_z)
        turn_rate = 14.0 if moving else 8.0
        blend = min(1.0, dt * turn_rate)
        self.facing_yaw = _lerp_angle(self.facing_yaw, target_yaw, blend)

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

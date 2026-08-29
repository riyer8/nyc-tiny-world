"""Shared keyboard controls for 2D and 3D play modes."""

from __future__ import annotations

import math
from dataclasses import dataclass

WALK_SPEED = 6.0
SPRINT_MULTIPLIER = 2.5
WORLD_SPEED_MULTIPLIER = 2.5

CONTROLS_HELP = (
    "Move: WASD or Arrow keys (W/↑ forward)  ·  Sprint: Space  ·  "
    "Look: Mouse  ·  Interact: E  ·  Quit: Esc"
)


@dataclass(frozen=True)
class MovementInput:
    """Normalized movement from keyboard."""

    forward: float = 0.0
    strafe: float = 0.0
    sprint: bool = False

    @property
    def active(self) -> bool:
        return self.forward != 0.0 or self.strafe != 0.0

    @property
    def speed_multiplier(self) -> float:
        return SPRINT_MULTIPLIER if self.sprint else 1.0


def read_movement(keys) -> MovementInput:
    """Read WASD + arrow keys. Forward = W or Up arrow."""
    from pygame.locals import (
        K_DOWN,
        K_LEFT,
        K_RIGHT,
        K_SPACE,
        K_UP,
        K_a,
        K_d,
        K_s,
        K_w,
    )

    forward = 0.0
    strafe = 0.0
    if keys[K_w] or keys[K_UP]:
        forward += 1.0
    if keys[K_s] or keys[K_DOWN]:
        forward -= 1.0
    if keys[K_a] or keys[K_LEFT]:
        strafe -= 1.0
    if keys[K_d] or keys[K_RIGHT]:
        strafe += 1.0

    length = math.hypot(forward, strafe)
    if length > 0:
        forward /= length
        strafe /= length

    return MovementInput(forward=forward, strafe=strafe, sprint=bool(keys[K_SPACE]))


def movement_delta_3d(
    movement: MovementInput,
    yaw: float,
    base_speed: float = WALK_SPEED,
    dt: float = 0.0,
) -> tuple[float, float]:
    """Convert movement input to world-space (dx, dz) for first-person view."""
    if not movement.active:
        return 0.0, 0.0

    speed = base_speed * movement.speed_multiplier * dt
    move_x = movement.forward * math.sin(yaw) + movement.strafe * math.cos(yaw)
    move_z = movement.forward * math.cos(yaw) - movement.strafe * math.sin(yaw)
    length = math.hypot(move_x, move_z)
    if length == 0:
        return 0.0, 0.0
    return move_x / length * speed, move_z / length * speed


def movement_delta_2d(
    movement: MovementInput,
    base_speed: float,
    dt: float,
) -> tuple[float, float]:
    """Convert movement input to screen-space (dx, dy) for top-down view."""
    if not movement.active:
        return 0.0, 0.0

    speed = base_speed * movement.speed_multiplier * dt
    # Screen y grows downward; forward (W/↑) moves up on screen.
    dx = movement.strafe * speed
    dy = -movement.forward * speed
    return dx, dy


def world_speed_multiplier(sprint: bool) -> float:
    """Speed multiplier for NPCs, vehicles, and world clock when sprinting."""
    return WORLD_SPEED_MULTIPLIER if sprint else 1.0

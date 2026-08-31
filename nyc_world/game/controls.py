"""Shared keyboard controls for 2D and 3D play modes."""

from __future__ import annotations

import math
from dataclasses import dataclass

WALK_SPEED = 6.0
SPRINT_MULTIPLIER = 2.5
WORLD_SPEED_MULTIPLIER = 2.5
JUMP_SPEED = 5.5
GRAVITY = 18.0
MAX_PITCH = 1.4

CONTROLS_HELP_2D = (
    "Move: WASD or Arrow keys (W/↑ forward)  ·  Sprint: F  ·  Quit: Esc"
)

CONTROLS_HELP_3D = (
    "Move: WASD/Arrows  ·  Sprint: F  ·  Jump: Space  ·  "
    "Look: click + mouse  ·  Interact: E  ·  Twin: T  ·  Photo: P  ·  Imagine: I  ·  "
    "God: ` or Shift+G  ·  Evolution: J  ·  Mystery: M  ·  Accuse: Y  ·  Subway: 1-6  ·  Esc: quit"
)

# Backward-compatible alias for 2D scripts.
CONTROLS_HELP = CONTROLS_HELP_2D


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
        K_f,
        K_LEFT,
        K_RIGHT,
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

    return MovementInput(forward=forward, strafe=strafe, sprint=bool(keys[K_f]))


@dataclass
class MouseLook:
    """Click-to-toggle camera orbit (third-person)."""

    active: bool = False
    sensitivity: float = 0.0025
    default_pitch: float = -0.28

    def toggle(self) -> bool:
        self.active = not self.active
        return self.active

    def apply(self, mx: float, my: float, yaw: float, pitch: float) -> tuple[float, float]:
        if not self.active:
            return yaw, pitch
        yaw -= mx * self.sensitivity
        pitch -= my * self.sensitivity
        from nyc_world.render.camera import MAX_PITCH, MIN_PITCH

        pitch = max(MIN_PITCH, min(MAX_PITCH, pitch))
        return yaw, pitch


@dataclass
class JumpState:
    """Simple vertical jump for the 3D player."""

    height: float = 0.0
    velocity: float = 0.0
    gravity: float = GRAVITY
    jump_speed: float = JUMP_SPEED

    @property
    def on_ground(self) -> bool:
        return self.height <= 0.0 and self.velocity <= 0.0

    def start_jump(self) -> bool:
        if not self.on_ground:
            return False
        self.velocity = self.jump_speed
        return True

    def update(self, dt: float) -> float:
        if self.height > 0.0 or self.velocity > 0.0:
            self.velocity -= self.gravity * dt
            self.height += self.velocity * dt
            if self.height < 0.0:
                self.height = 0.0
                self.velocity = 0.0
        return self.height


def camera_basis(yaw: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Horizontal forward/right unit vectors matching the OpenGL camera."""
    forward = (math.sin(yaw), -math.cos(yaw))
    right = (math.cos(yaw), math.sin(yaw))
    return forward, right


def movement_delta_3d(
    movement: MovementInput,
    yaw: float,
    base_speed: float = WALK_SPEED,
    dt: float = 0.0,
) -> tuple[float, float]:
    """Move relative to where the camera is facing (W/↑ = forward)."""
    if not movement.active:
        return 0.0, 0.0

    speed = base_speed * movement.speed_multiplier * dt
    forward, right = camera_basis(yaw)
    move_x = movement.forward * forward[0] + movement.strafe * right[0]
    move_z = movement.forward * forward[1] + movement.strafe * right[1]
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

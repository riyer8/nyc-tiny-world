"""Tests for shared keyboard controls."""

from __future__ import annotations

import math

import pytest

from nyc_world.game.controls import (
    MovementInput,
    movement_delta_2d,
    movement_delta_3d,
    read_movement,
    world_speed_multiplier,
)


class _FakeKeys(dict):
    def __getitem__(self, key):
        return self.get(key, False)


def test_read_movement_wasd_and_arrows():
    from pygame.locals import K_UP, K_w

    keys = _FakeKeys({K_w: True, K_UP: True})
    movement = read_movement(keys)
    assert movement.forward == 1.0
    assert movement.strafe == 0.0


def test_read_movement_sprint():
    from pygame.locals import K_f, K_w

    keys = _FakeKeys({K_w: True, K_f: True})
    movement = read_movement(keys)
    assert movement.sprint is True
    assert movement.speed_multiplier > 1.0


def test_mouse_look_toggle_and_apply():
    from nyc_world.game.controls import MouseLook

    look = MouseLook()
    assert look.active
    yaw, pitch = look.apply(10, 5, 0.0, 0.0)
    assert yaw != 0.0
    assert pitch != 0.0
    look.toggle()
    assert not look.active
    yaw2, pitch2 = look.apply(10, 5, yaw, pitch)
    assert yaw2 == yaw
    assert pitch2 == pitch


def test_jump_state():
    from nyc_world.game.controls import JumpState

    jump = JumpState()
    assert jump.on_ground
    assert jump.start_jump()
    jump.update(0.05)
    assert jump.height > 0.0
    for _ in range(80):
        jump.update(0.05)
    assert jump.on_ground


def test_movement_delta_3d_forward():
    movement = MovementInput(forward=1.0, strafe=0.0, sprint=False)
    dx, dz = movement_delta_3d(movement, yaw=math.pi / 2, dt=1.0)
    assert dx == pytest.approx(6.0, abs=0.01)
    assert dz == pytest.approx(0.0, abs=0.01)


def test_movement_follows_camera_yaw():
    movement = MovementInput(forward=1.0)
    _, dz_north = movement_delta_3d(movement, yaw=math.pi, dt=1.0)
    assert dz_north > 0
    _, dz_south = movement_delta_3d(movement, yaw=0.0, dt=1.0)
    assert dz_south < 0
    dx_east, _ = movement_delta_3d(movement, yaw=math.pi / 2, dt=1.0)
    assert dx_east > 0


def test_strafe_relative_to_camera_yaw():
    movement = MovementInput(strafe=1.0)
    dx, dz = movement_delta_3d(movement, yaw=math.pi / 2, dt=1.0)
    assert dx == pytest.approx(0.0, abs=0.01)
    assert dz > 0


def test_movement_delta_2d_up_moves_negative_y():
    movement = MovementInput(forward=1.0)
    dx, dy = movement_delta_2d(movement, base_speed=10.0, dt=1.0)
    assert dx == 0.0
    assert dy < 0.0


def test_world_speed_multiplier():
    assert world_speed_multiplier(False) == 1.0
    assert world_speed_multiplier(True) > 1.0

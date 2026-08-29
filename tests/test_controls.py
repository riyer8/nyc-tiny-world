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
    from pygame.locals import K_SPACE, K_w

    keys = _FakeKeys({K_w: True, K_SPACE: True})
    movement = read_movement(keys)
    assert movement.sprint is True
    assert movement.speed_multiplier > 1.0


def test_movement_delta_3d_forward():
    movement = MovementInput(forward=1.0, strafe=0.0, sprint=False)
    dx, dz = movement_delta_3d(movement, yaw=math.pi / 2, dt=1.0)
    assert dx == pytest.approx(6.0, abs=0.01)
    assert dz == pytest.approx(0.0, abs=0.01)


def test_movement_delta_2d_up_moves_negative_y():
    movement = MovementInput(forward=1.0)
    dx, dy = movement_delta_2d(movement, base_speed=10.0, dt=1.0)
    assert dx == 0.0
    assert dy < 0.0


def test_world_speed_multiplier():
    assert world_speed_multiplier(False) == 1.0
    assert world_speed_multiplier(True) > 1.0

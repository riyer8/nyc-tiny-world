"""Tests for third-person camera."""

from __future__ import annotations

import math

from nyc_world.game.player_avatar import PlayerAvatar
from nyc_world.render.camera import third_person_camera_eye, third_person_look_at


def test_camera_behind_player():
    ex, ey, ez = third_person_camera_eye(100, 0, 200, yaw=0, pitch=-0.3)
    # yaw=0 faces -z, camera should be behind (+z) and elevated
    assert ez > 200
    assert ey > 1.0
    assert abs(ex - 100) < 2.0  # slight side offset only


def test_camera_side_offset():
    ex1, _, _ = third_person_camera_eye(0, 0, 0, yaw=0, pitch=-0.3)
    ex2, _, ez2 = third_person_camera_eye(0, 0, 0, yaw=math.pi / 2, pitch=-0.3)
    assert ex1 != ex2 or ez2 != ex1


def test_look_at_chest_height():
    assert third_person_look_at(0.5) > 0.5


def test_avatar_walk_phase_advances():
    av = PlayerAvatar()
    av.update(0.1, moving=True, sprinting=False)
    assert av.walk_phase > 0

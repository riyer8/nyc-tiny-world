"""Tests for player avatar facing and building collision."""

from __future__ import annotations

import math

import pytest

from nyc_world.core.collision import BuildingCollision
from nyc_world.game.player_avatar import PlayerAvatar, camera_facing_yaw
from nyc_world.map.buildings import Building3D
from nyc_world.render.meshes import window_grid


def test_camera_facing_yaw_matches_movement_heading() -> None:
  # Camera yaw π looks down +Z — same heading NPCs use when walking north.
  assert camera_facing_yaw(math.pi) == pytest.approx(0.0)
  assert camera_facing_yaw(0.0) == pytest.approx(math.pi)
  assert camera_facing_yaw(math.pi / 2) == pytest.approx(math.pi / 2)


def test_avatar_faces_movement_direction() -> None:
  avatar = PlayerAvatar()
  for _ in range(30):
    avatar.update(0.05, moving=True, sprinting=False, move_x=1.0, move_z=0.0, camera_yaw=0.0)
  assert avatar.facing_yaw == pytest.approx(math.pi / 2, abs=0.05)


def test_building_collision_blocks_interior_point() -> None:
  building = Building3D(
    footprint=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
    height=12.0,
    wall_r=0.5,
    wall_g=0.5,
    wall_b=0.5,
    roof_r=0.4,
    roof_g=0.4,
    roof_b=0.4,
  )
  collision = BuildingCollision([building], inset_m=0.5)
  assert collision.is_blocked(5.0, 5.0, radius=0.6)
  assert not collision.is_blocked(-1.0, 5.0, radius=0.6)


def test_building_dist_uses_nearest_wall() -> None:
  from nyc_world.render.meshes import _building_dist_sq

  building = Building3D(
    footprint=((0.0, 0.0), (20.0, 0.0), (20.0, 10.0), (0.0, 10.0)),
    height=12.0,
    wall_r=0.5,
    wall_g=0.5,
    wall_b=0.5,
    roof_r=0.4,
    roof_g=0.4,
    roof_b=0.4,
  )
  # Player beside the long face — much closer than building center.
  assert _building_dist_sq(building, -2.0, 5.0) == pytest.approx(4.0)
  assert _building_dist_sq(building, 10.0, 5.0) == pytest.approx(0.0)


def test_building_collision_push_out() -> None:
  building = Building3D(
    footprint=((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)),
    height=12.0,
    wall_r=0.5,
    wall_g=0.5,
    wall_b=0.5,
    roof_r=0.4,
    roof_g=0.4,
    roof_b=0.4,
  )
  collision = BuildingCollision([building], inset_m=0.5)
  x, z = collision.push_out(5.0, 5.0, radius=0.6, ox=-1.0, oz=5.0)
  assert not collision.is_blocked(x, z, radius=0.6)
  assert x < 1.0 or x > 9.0 or z < 1.0 or z > 9.0


def test_window_grid_scales_with_height() -> None:
  tower = Building3D(
    footprint=((0.0, 0.0), (28.0, 0.0), (28.0, 16.0), (0.0, 16.0)),
    height=128.0,
    wall_r=0.4,
    wall_g=0.45,
    wall_b=0.55,
    roof_r=0.3,
    roof_g=0.35,
    roof_b=0.4,
    levels=40,
  )
  stories, cols = window_grid(tower, 28.0, detail="full")
  assert stories == 40
  assert cols >= 8
  medium_stories, medium_cols = window_grid(tower, 28.0, detail="medium")
  assert medium_stories == 10
  assert medium_cols == 1


def test_nearby_window_quads_stay_bounded() -> None:
    from nyc_world.core import GeoProjection, World, World3D
    from nyc_world.paths import DEFAULT_MAP_PATH, DEFAULT_META_PATH
    from nyc_world.render.meshes import count_window_quads

    if not DEFAULT_MAP_PATH.exists() or not DEFAULT_META_PATH.exists():
        pytest.skip("map data missing")
    world = World.from_file(DEFAULT_MAP_PATH)
    world3d = World3D(world)
    px, _, pz = world3d.spawn
    counts = count_window_quads(world3d.buildings, px, pz)
    assert counts["full"] + counts["medium"] < 80_000


def test_low_rise_gets_windows() -> None:
  house = Building3D(
    footprint=((0.0, 0.0), (10.0, 0.0), (10.0, 8.0), (0.0, 8.0)),
    height=10.0,
    wall_r=0.5,
    wall_g=0.3,
    wall_b=0.25,
    roof_r=0.4,
    roof_g=0.3,
    roof_b=0.2,
    levels=3,
  )
  stories, cols = window_grid(house, 10.0, detail="full")
  assert stories == 3
  assert cols >= 3

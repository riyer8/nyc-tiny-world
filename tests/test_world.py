"""Tests for the 2D world and collision."""

import pytest

from nyc_world.paths import DEFAULT_MAP_PATH, DEFAULT_META_PATH
from nyc_world.projection import GeoProjection
from nyc_world.sprites import BUILDING, ROAD
from nyc_world.world import World
from nyc_world.world_3d import World3D


@pytest.fixture
def world() -> World:
    if not DEFAULT_MAP_PATH.exists():
        pytest.skip("Run scripts/generate_map.py first")
    return World.from_file(DEFAULT_MAP_PATH)


def test_world_loads_map(world: World) -> None:
    assert world.cols > 0
    assert world.rows > 0
    assert world.projection is not None


def test_spawn_is_walkable(world: World) -> None:
    ts = world.tile_size
    col = int(world.player_spawn[0] // ts)
    row = int(world.player_spawn[1] // ts)
    assert not world.is_solid(col, row)


def test_building_tiles_are_solid(world: World) -> None:
    found = False
    for row in range(world.rows):
        for col in range(world.cols):
            if world.tile_at(col, row) == BUILDING:
                assert world.is_solid(col, row)
                found = True
                break
        if found:
            break
    assert found


def test_world3d_loads_buildings(world: World) -> None:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    world3d = World3D(world)
    assert len(world3d.buildings) > 100
    assert world3d.spawn[1] == pytest.approx(1.7)


def test_world3d_collision_at_spawn(world: World) -> None:
    world3d = World3D(world)
    x, _, z = world3d.spawn
    assert not world3d.is_blocked(x, z)

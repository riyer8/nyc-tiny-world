"""Tests for street network and pathfinding."""

import json

import pytest

from nyc_world.pathfinding import astar, build_adjacency, set_astar_positions
from nyc_world.paths import DATA_DIR, DEFAULT_META_PATH
from nyc_world.projection import GeoProjection
from nyc_world.streets import load_street_network


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_build_adjacency() -> None:
    graph = build_adjacency([(1, 2, 10.0), (2, 3, 5.0)])
    assert len(graph[1]) == 1
    assert graph[1][0][0] == 2


def test_astar_simple() -> None:
    set_astar_positions({1: (0, 0), 2: (10, 0), 3: (10, 10)})
    graph = build_adjacency([(1, 2, 10), (2, 3, 10)])
    path = astar(graph, 1, 3)
    assert path == [1, 2, 3]


def test_street_network_loads(projection: GeoProjection) -> None:
    osm_path = DATA_DIR / "greenwich_village_osm.json"
    if not osm_path.exists():
        pytest.skip("No OSM cache")
    streets = load_street_network(projection)
    assert streets is not None
    assert len(streets.scene.road_quads) > 100
    assert len(streets.walk_graph) > 50
    assert len(streets.drive_graph) > 50

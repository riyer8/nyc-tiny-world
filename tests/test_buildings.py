"""Tests for building height estimation and OSM loading."""

import json

import pytest

from nyc_world.core import GeoProjection
from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.map.buildings import (
    estimate_height_m,
    load_buildings,
    load_buildings_for_area,
)
from nyc_world.paths import DATA_DIR, DEFAULT_META_PATH

OSM_PATH = DATA_DIR / "greenwich_village_osm.json"


def test_untagged_yes_buildings_vary_by_footprint() -> None:
    projection = GeoProjection.from_area(WASHINGTON_SQUARE, cols=40, rows=40, tile_size=32)
    osm = {
        "elements": [
            {"type": "node", "id": 1, "lat": 40.7290, "lon": -73.9995},
            {"type": "node", "id": 2, "lat": 40.7290, "lon": -73.9993},
            {"type": "node", "id": 3, "lat": 40.7292, "lon": -73.9993},
            {"type": "node", "id": 4, "lat": 40.7292, "lon": -73.9995},
            {"type": "node", "id": 5, "lat": 40.7320, "lon": -73.9955},
            {"type": "node", "id": 6, "lat": 40.7320, "lon": -73.9953},
            {"type": "node", "id": 7, "lat": 40.7322, "lon": -73.9953},
            {"type": "node", "id": 8, "lat": 40.7322, "lon": -73.9955},
            {
                "type": "way",
                "id": 10,
                "nodes": [1, 2, 3, 4, 1],
                "tags": {"building": "yes"},
            },
            {
                "type": "way",
                "id": 11,
                "nodes": [5, 6, 7, 8, 5],
                "tags": {"building": "yes"},
            },
        ]
    }
    buildings = load_buildings(projection, osm)
    assert len(buildings) == 2
    walls = {(b.wall_r, b.wall_g, b.wall_b) for b in buildings}
    assert len(walls) == 2


def test_estimate_height_from_osm_tag() -> None:
    assert estimate_height_m({"height": "50.0"}) == 50.0
    assert estimate_height_m({"height": "30 ft"}) == pytest.approx(9.144, rel=0.01)


def test_estimate_height_from_levels() -> None:
    assert estimate_height_m({"building:levels": "10"}) == 35.0


def test_estimate_height_from_building_type() -> None:
    assert estimate_height_m({"building": "house"}) == 7.0
    assert estimate_height_m({"building": "office"}) == 42.0


def test_load_buildings_from_cache() -> None:
    if not OSM_PATH.exists() or not DEFAULT_META_PATH.exists():
        pytest.skip("Run scripts/generate_map.py first")
    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    osm_data = json.loads(OSM_PATH.read_text())
    buildings = load_buildings(projection, osm_data)
    assert len(buildings) > 100
    assert all(len(b.footprint) >= 3 for b in buildings)
    assert all(3.0 <= b.height <= 280.0 for b in buildings)


def test_load_buildings_for_area() -> None:
    if not OSM_PATH.exists() or not DEFAULT_META_PATH.exists():
        pytest.skip("Run scripts/generate_map.py first")
    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    buildings = load_buildings_for_area(projection)
    assert len(buildings) > 100

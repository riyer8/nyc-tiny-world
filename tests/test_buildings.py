"""Tests for building height estimation and OSM loading."""

import json
from pathlib import Path

import pytest

from nyc_world.buildings import (
    estimate_height_m,
    load_buildings,
    load_buildings_for_area,
)
from nyc_world.paths import DATA_DIR, DEFAULT_META_PATH
from nyc_world.projection import GeoProjection

OSM_PATH = DATA_DIR / "greenwich_village_osm.json"


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

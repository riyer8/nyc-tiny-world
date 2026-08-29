"""Tests for streaming world architecture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import gps_to_world_xz, world_xz_to_gps
from nyc_world.map.buildings import Building3D
from nyc_world.streaming.loader import TileDataLoader
from nyc_world.streaming.lod import lod_buildings
from nyc_world.streaming.radii import DEFAULT_RADII, StreamRadii
from nyc_world.streaming.tiles import (
    TILE_SIZE_M,
    gps_to_tile,
    tile_bbox,
    tiles_within_radius,
)
from nyc_world.streaming.world_manager import StreamingWorldManager


def test_stream_radii_defaults():
    assert DEFAULT_RADII.data_m == pytest.approx(5 * 1609.344, rel=0.01)
    assert DEFAULT_RADII.render_3d_m == pytest.approx(1609.344, rel=0.01)
    assert DEFAULT_RADII.simulation_m == 300.0
    assert DEFAULT_RADII.interaction_m == 100.0


def test_gps_to_tile_round_trip():
    lat, lon = WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon
    tile = gps_to_tile(lat, lon)
    south, west, north, east = tile_bbox(tile)
    assert south <= lat <= north
    assert west <= lon <= east


def test_tiles_within_radius():
    lat, lon = WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon
    tiles = tiles_within_radius(lat, lon, 1000.0)
    assert len(tiles) >= 4
    assert all(isinstance(t.tile_id, str) for t in tiles)


def test_tile_loader_cache(tmp_path: Path):
    loader = TileDataLoader(cache_dir=tmp_path, network=False)
    tile = gps_to_tile(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon)
    fake = {"elements": [{"type": "node", "id": 1, "lat": 40.73, "lon": -73.99}]}
    path = loader.tile_path(tile)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fake))

    data = loader.ensure_tile(tile)
    assert data is not None
    assert loader.loaded[tile.tile_id]["elements"][0]["id"] == 1


def test_lod_buildings_filters_by_distance():
    radii = StreamRadii(render_3d_m=50.0, data_m=200.0)
    near = Building3D(((0, 0), (10, 0), (10, 10), (0, 10)), 10, 0.5, 0.5, 0.5, 0.4, 0.4, 0.4)
    far = Building3D(((200, 200), (210, 200), (210, 210), (200, 210)), 10, 0.5, 0.5, 0.5, 0.4, 0.4, 0.4)
    detailed, markers = lod_buildings([near, far], 5, 5, radii)
    assert len(detailed) == 1
    assert len(markers) == 1


def test_streaming_world_manager_updates_tiles():
    proj = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    mpt = proj.meters_per_tile()
    x, z = gps_to_world_xz(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, proj)
    buildings = [
        Building3D(((x, z), (x + 10, z), (x + 10, z + 10), (x, z + 10)), 12, 0.5, 0.5, 0.5, 0.4, 0.4, 0.4)
    ]
    mgr = StreamingWorldManager(proj, mpt, x, z, buildings, npc_count=2, vehicle_count=2)
    state = mgr.update_player(x, z)
    assert state.player_tile
    assert state.buildings_in_render >= 1

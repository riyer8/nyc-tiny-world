"""Tests for geographic grounding and coordinate transforms."""

from __future__ import annotations

import math

import pytest

from nyc_world.core.areas import GREENWICH_VILLAGE, WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import (
    game_px_to_world_xz,
    gps_to_world_xz,
    world_xz_to_game_px,
    world_xz_to_gps,
)
from nyc_world.geo.context import nearest_named_street
from nyc_world.city.streets import NamedStreetSegment, StreetNetwork, StreetScene


def _projection(area=GREENWICH_VILLAGE) -> GeoProjection:
    return GeoProjection.from_area(area, cols=80, rows=80, tile_size=16)


def test_world_xz_gps_round_trip():
    proj = _projection()
    mpt = proj.meters_per_tile()
    lat, lon = WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon
    x, z = gps_to_world_xz(lat, lon, proj)
    lat2, lon2 = world_xz_to_gps(x, z, proj, mpt)
    assert lat2 == pytest.approx(lat, abs=1e-5)
    assert lon2 == pytest.approx(lon, abs=1e-5)


def test_game_px_world_xz_round_trip():
    proj = _projection()
    mpt = proj.meters_per_tile()
    gx, gy = proj.to_game(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon)
    x, z = game_px_to_world_xz(gx, gy, proj, mpt)
    gx2, gy2 = world_xz_to_game_px(x, z, proj, mpt)
    x2, z2 = game_px_to_world_xz(gx2, gy2, proj, mpt)
    assert x2 == pytest.approx(x, abs=0.01)
    assert z2 == pytest.approx(z, abs=0.01)


def test_washington_square_bbox_is_smaller():
    gv = GeoProjection.from_area(GREENWICH_VILLAGE, cols=80, rows=80, tile_size=16)
    ws = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    assert ws.east_span_m < gv.east_span_m
    assert ws.north_span_m < gv.north_span_m
    assert ws.east_span_m == pytest.approx(500, abs=80)
    assert ws.north_span_m == pytest.approx(500, abs=80)


def test_nearest_named_street():
    streets = StreetNetwork(
        positions={},
        walk_graph={},
        drive_graph={},
        scene=StreetScene(),
        intersection_nodes=set(),
        named_segments=[
            NamedStreetSegment("Washington Pl", "residential", 0, 0, 20, 0),
            NamedStreetSegment("Broadway", "primary", 100, 100, 100, 120),
        ],
    )
    name, dist = nearest_named_street(streets, 10, 1)
    assert name == "Washington Pl"
    assert dist < 5

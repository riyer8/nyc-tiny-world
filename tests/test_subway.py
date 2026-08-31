"""Tests for subway graph, travel times, and GPS projection."""

from __future__ import annotations

import math

import pytest

from nyc_world.city.subway import (
    SubwaySimulation,
    build_subway_graph,
)
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import gps_to_world_xz, world_xz_to_gps
from nyc_world.paths import DEFAULT_META_PATH


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_graph_connectivity():
    graph = build_subway_graph()
    for sid in graph.stations:
        for other in graph.stations:
            if sid == other:
                continue
            route, seconds = graph.route(sid, other)
            assert route, f"No route {sid} -> {other}"
            assert seconds < float("inf")


def test_w4_to_union_sq_under_60_seconds():
    graph = build_subway_graph()
    _, seconds = graph.route("w4", "union_sq")
    assert seconds <= 60.0


def test_gps_round_trip(projection: GeoProjection):
    graph = build_subway_graph(projection)
    for station in graph.stations.values():
        lat, lon = station.latlon
        x, z = gps_to_world_xz(lat, lon, projection)
        mpt = projection.meters_per_tile()
        lat2, lon2 = world_xz_to_gps(x, z, projection, mpt)
        assert abs(lat2 - lat) < 0.002
        assert abs(lon2 - lon) < 0.002


def test_player_ride_completes():
    graph = build_subway_graph()
    sim = SubwaySimulation(graph=graph)
    ride = sim.start_ride("player", "w4", "union_sq")
    assert ride is not None
    assert ride.duration_s <= 60.0
    finished = sim.update(ride.duration_s + 1.0)
    assert finished
    assert finished[0].complete
    pos = sim.exit_position(finished[0])
    dest = graph.stations["union_sq"].entrance_xz
    assert math.hypot(pos[0] - dest[0], pos[1] - dest[1]) < 1.0


def test_commuter_subway_usage_in_rain():
    graph = build_subway_graph()
    sim = SubwaySimulation(graph=graph)
    w4 = graph.stations["w4"].entrance_xz
    union = graph.stations["union_sq"].entrance_xz

    class FakeNPC:
        personality = "commuter"
        x = w4[0]
        z = w4[1]
        path: list = []
        path_index = 0
        agent_action = ""

    riders = 0
    attempts = 20
    for _ in range(attempts):
        npc = FakeNPC()
        if sim.try_npc_ride(
            npc,
            target_x=union[0],
            target_z=union[1],
            is_raining=True,
            min_distance=60.0,
        ):
            riders += 1
    sim.commuter_count = attempts
    assert riders / attempts >= 0.1

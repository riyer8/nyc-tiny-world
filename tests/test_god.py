"""Tests for god / sandbox mode."""

from __future__ import annotations

import pytest

from nyc_world.city.pathfinding import astar, set_astar_positions
from nyc_world.city.vehicles import Vehicle
from nyc_world.city.world_clock import Weather
from nyc_world.feeds.types import CityEvent
from nyc_world.modes.god import GodMode, GodPatch
from nyc_world.simulation.event_log import EventLog


def _linear_graph() -> dict[int, list[tuple[int, float]]]:
    return {
        0: [(1, 1.0)],
        1: [(0, 1.0), (2, 1.0)],
        2: [(1, 1.0)],
    }


def test_god_patch_roundtrip():
    patch = GodPatch(
        time_hour=12,
        time_minute=30,
        weather_override="rain",
        active_events=[CityEvent(title="Festival", location="park", start_hour=14)],
        road_closures=["1:2"],
    )
    restored = GodPatch.from_dict(patch.to_dict())
    assert restored.time_hour == 12
    assert restored.weather_override == "rain"
    assert restored.road_closures == ["1:2"]
    assert restored.active_events[0].title == "Festival"


def test_astar_avoids_blocked_edge():
    graph = _linear_graph()
    set_astar_positions({0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0)})
    path = astar(graph, 0, 2)
    assert path == [0, 1, 2]
    blocked = {(1, 2)}
    assert astar(graph, 0, 2, blocked_edges=blocked) == []


def test_god_time_and_weather():
    from nyc_world.city.city_sim import CitySimulation
    from nyc_world.core.projection import GeoProjection
    from nyc_world.paths import DEFAULT_META_PATH

    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    city = CitySimulation(projection, 100.0, 100.0, npc_count=2, vehicle_count=0)
    god = GodMode()
    log = EventLog()

    god.apply_time(city, 6, 15, event_log=log)
    assert city.clock.hour == 6
    assert city.clock.minute == 15
    assert log.entries[-1].action == "set_time"

    god.apply_weather(city, "rain", event_log=log)
    assert city.clock.weather == Weather.RAIN
    assert log.entries[-1].action == "set_weather"


def test_festival_increases_npc_count():
    from nyc_world.city.city_sim import CitySimulation
    from nyc_world.core.projection import GeoProjection
    from nyc_world.paths import DEFAULT_META_PATH

    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    god = GodMode()
    before = len(city.npcs)
    spawned = god.spawn_festival(city, 50.0, 50.0, count=5)
    assert spawned == 5
    assert len(city.npcs) == before + 5
    assert god.festival_active
    assert god.crowd_boost_pct() > 0
    god.remove_festival(city)
    assert len(city.npcs) == before


def test_road_closure_reroutes_vehicles():
    from nyc_world.city.streets import StreetNetwork, StreetScene

    graph = _linear_graph()
    positions = {0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0)}
    streets = StreetNetwork(
        positions=positions,
        walk_graph=graph,
        drive_graph=graph,
        scene=StreetScene(),
        intersection_nodes={1},
    )
    set_astar_positions(positions)
    vehicle = Vehicle(kind="car", x=0.0, z=0.0)
    vehicle._new_route(streets)
    assert len(vehicle.path) > 0

    god = GodMode()
    city = type(
        "City",
        (),
        {
            "streets": streets,
            "vehicles": [vehicle],
            "clock": type("C", (), {"day": 1, "time_str": "12:00"})(),
        },
    )()
    assert god.close_road(city)  # type: ignore[arg-type]
    assert streets.blocked_edges
    assert astar(graph, 0, 2, blocked_edges=streets.blocked_edges) == []


def test_clear_road_closures():
    god = GodMode()
    god.blocked_edges.add((1, 2))
    god.patch.road_closures.append("1:2")
    from nyc_world.city.streets import StreetNetwork, StreetScene

    streets = StreetNetwork(
        positions={0: (0.0, 0.0), 1: (1.0, 0.0), 2: (2.0, 0.0)},
        walk_graph=_linear_graph(),
        drive_graph=_linear_graph(),
        scene=StreetScene(),
        intersection_nodes=set(),
        blocked_edges={(1, 2)},
    )
    city = type(
        "City",
        (),
        {
            "streets": streets,
            "vehicles": [],
            "clock": type("C", (), {"day": 1, "time_str": "12:00"})(),
        },
    )()
    god.clear_road_closures(city)  # type: ignore[arg-type]
    assert not god.blocked_edges
    assert not streets.blocked_edges
    assert not god.patch.road_closures

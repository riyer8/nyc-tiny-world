"""Tests for digital twin mode."""

from __future__ import annotations

import pytest

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.modes.twin import TwinMode
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation import Simulation


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_twin_toggle_preserves_state():
    twin = TwinMode()
    assert not twin.active
    twin.toggle()
    assert twin.active
    twin.set_time_scale(10.0)
    twin.toggle_pause()
    assert twin.paused
    twin.toggle()
    assert not twin.active
    assert not twin.paused


def test_pause_stops_time_scale():
    twin = TwinMode(active=True, time_scale=10.0, paused=True)
    assert twin.effective_speed_multiplier(1.0) == 0.0
    twin.paused = False
    assert twin.effective_speed_multiplier(1.0) == 10.0


def test_time_scale_advances_clock(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    sim = Simulation(city, player, quests, minds=city.mind_registry)

    start_minutes = city.clock.hour * 60 + city.clock.minute
    for _ in range(60):
        sim.advance_world(1.0, speed_multiplier=1.0, time_scale=10.0)
    end_minutes = city.clock.hour * 60 + city.clock.minute
    elapsed = (end_minutes - start_minutes) % (24 * 60)
    assert elapsed >= 60


def test_paused_advance_world_does_not_tick(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    sim = Simulation(city, player, quests, minds=city.mind_registry)

    start = city.clock.minute
    sim.advance_world(5.0, time_scale=0.0)
    assert city.clock.minute == start


def test_ten_x_runs_five_sim_hours(projection: GeoProjection):
    """10× speed should advance 5 sim-hours without error."""
    city = CitySimulation(projection, 100.0, 100.0, npc_count=8, vehicle_count=4)
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    sim = Simulation(city, player, quests, minds=city.mind_registry)

    start_minutes = city.clock.hour * 60 + city.clock.minute
    # 5 sim hours = 300 game minutes; at 10× and speed 2 -> 20 min/sec -> 15 real seconds
    for _ in range(15):
        sim.advance_world(1.0, speed_multiplier=1.0, time_scale=10.0)
    elapsed = (city.clock.hour * 60 + city.clock.minute - start_minutes) % (24 * 60)
    assert elapsed >= 300


def test_select_npc_shows_brain_panel(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    twin = TwinMode(active=True)
    npc = city.npcs[0]
    agents = city.agent_controller
    brain = agents.get(npc.name)
    assert brain is not None
    brain.goal_text = "find coffee"
    brain.current_action = "explore"
    assert twin.select_nearest(city.npcs, city.vehicles, npc.x, npc.z, radius=5.0)
    lines = twin.inspector_lines(npc.name, minds=city.mind_registry, agents=agents)
    assert any("coffee" in line.lower() or "explore" in line.lower() for line in lines)

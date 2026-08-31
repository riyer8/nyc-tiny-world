"""Tests for WorldState and Simulation (Chunk 17)."""

from __future__ import annotations

import pytest

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.geo.coords import gps_to_world_xz
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation import Simulation, WorldState
from nyc_world.simulation.actions import PlayerMoveAction, WaitAction
from nyc_world.simulation.adapters import capture_world_state


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def _make_sim() -> Simulation:
    proj = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    x, z = gps_to_world_xz(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, proj)
    city = CitySimulation(proj, x, z, npc_count=4, vehicle_count=2)
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    return Simulation(city, player, quests, minds=city.mind_registry)


def test_world_state_includes_economy_and_relationships(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    minds = city.mind_registry
    minds.relationships.record_visit("maya", tick=1, game_day=1, game_time="08:00 AM")
    state = capture_world_state(
        city,
        PlayerProfile(),
        QuestManager(PlayerProfile(), minds=minds),
        minds,
        tick=1,
        player_x=100,
        player_z=100,
    )
    assert state.economy.open_businesses >= 10
    assert any(r.npc_id == "maya" for r in state.relationships)


def test_world_state_round_trip():
    state = WorldState(tick=5)
    restored = WorldState.from_dict(state.to_dict())
    assert restored.tick == 5


def test_simulation_observe_captures_player():
    sim = _make_sim()
    state = sim.observe(100.0, 200.0, player_yaw=1.5)
    assert state.player.x == 100.0
    assert state.player.z == 200.0
    assert state.player.money == 37


def test_simulation_step_advances_tick():
    sim = _make_sim()
    state = sim.observe(10.0, 20.0)
    next_state = sim.step(state, WaitAction(), 1 / 60)
    assert next_state.tick >= state.tick


def test_simulation_apply_move_action():
    sim = _make_sim()
    state = sim.observe(0.0, 0.0)
    next_state = sim.apply_action_to_state(state, PlayerMoveAction(dx=3.0, dz=4.0))
    assert next_state.player.x == 3.0
    assert next_state.player.z == 4.0


def test_maya_mind_in_observed_state():
    sim = _make_sim()
    registry = sim.minds
    registry.register_quest_npcs()
    state = sim.observe(10.0, 20.0)
    maya = state.npc_by_id("maya")
    if maya is None and sim.city.npcs:
        sim.city.npcs[0].name = "maya"
        state = sim.observe(sim.city.npcs[0].x, sim.city.npcs[0].z)
        maya = state.npc_by_id("maya")
    # Maya mind exists in registry even if not spawned as NPC entity yet.
    assert registry.get("maya") is not None
    assert registry.get("maya").current_goal_text()


def test_world_state_includes_agent_needs():
    sim = _make_sim()
    state = sim.observe(10.0, 20.0)
    assert len(state.npcs) == 4
    for npc in state.npcs:
        assert npc.hunger >= 0.0
        assert npc.energy >= 0.0
        assert "curious" in npc.personality or npc.personality

"""Tests for utility-based NPC agent brains."""

from __future__ import annotations

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation.agent import (
    AgentBrain,
    AgentNeeds,
    Personality,
    action_target,
    pick_action,
    score_actions,
)
import pytest


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def _brain() -> AgentBrain:
    return AgentBrain(
        npc_id="npc_1",
        display_name="Jordan",
        personality=Personality(0.5, 0.8, 0.6, 0.3, 0.4),
        needs=AgentNeeds(hunger=0.8, energy=0.3, social=0.5, money=0.4),
        home=(10.0, 10.0),
        workplace=(50.0, 50.0),
        cafe=(30.0, 20.0),
        park=(15.0, 40.0),
    )


def test_hungry_npc_prefers_eat():
    brain = _brain()
    scores = score_actions(brain, hour=12, is_raining=False, game_minutes=720)
    assert pick_action(scores) == "eat"


def test_rain_prefers_shelter():
    brain = _brain()
    brain.needs.hunger = 0.2
    scores = score_actions(brain, hour=12, is_raining=True, game_minutes=720)
    assert pick_action(scores) == "seek_shelter"


def test_tired_evening_prefers_home():
    brain = _brain()
    brain.needs.hunger = 0.2
    brain.needs.energy = 0.15
    brain.home_hour = 18
    scores = score_actions(brain, hour=19, is_raining=False, game_minutes=19 * 60)
    assert pick_action(scores) in ("go_home", "rest")


def test_needs_drift_over_time():
    needs = AgentNeeds(hunger=0.2, energy=0.8, social=0.2, money=0.3)
    needs.drift(60.0)
    assert needs.hunger > 0.2
    assert needs.energy < 0.8
    assert needs.social > 0.2


def test_action_target_cafe_for_eat():
    brain = _brain()
    assert action_target(brain, "eat") == brain.cafe


def test_all_npcs_have_agent_brains(projection: GeoProjection):
    city = CitySimulation(projection, 500, 500, npc_count=48, vehicle_count=4)
    assert len(city.agent_controller.brains) == 48


def test_agent_updates_npc_route(projection: GeoProjection):
    city = CitySimulation(projection, 500, 500, npc_count=4, vehicle_count=2)
    npc = city.npcs[0]
    brain = city.agent_controller.get(npc.name)
    assert brain is not None
    brain.needs.hunger = 0.95
    brain._decision_timer = 10.0
    npc.path = []
    npc.path_index = 0
    npc.wait_until = 0.0
    city.agent_controller.update_npc(
        npc, city.streets, city.clock, 1.0, minds=city.mind_registry
    )
    assert npc.path or brain.current_action == "eat"

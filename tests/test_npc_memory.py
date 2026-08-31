"""Pillar 1 acceptance tests — memory facts, opinions, dialogue routing."""

from __future__ import annotations

from pathlib import Path

import pytest

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.game.dialogue import pick_npc_greeting
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.game.save import apply_save, capture_save
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation.adapters import capture_world_state
from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.memory import make_fact, synthesize_opinion


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_maya_memory_panel_after_scripted_session(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    minds = city.mind_registry
    rel = minds.relationships.get("maya")

    minds.relationships.record_fact(
        "maya", "helped", "You found her camera",
        tick=1, game_day=1, game_time="08:00 AM", sentiment=0.8, friendship_delta=5,
    )
    minds.relationships.record_fact(
        "maya", "gave", "You gave her $10",
        tick=2, game_day=2, game_time="10:00 AM", amount=10, friendship_delta=3,
    )
    minds.relationships.record_fact(
        "maya", "stole", "You stole her coffee",
        tick=3, game_day=3, game_time="11:00 AM", sentiment=-0.9, trust_delta=-15,
    )
    minds.relationships.record_visit("maya", tick=4, game_day=3, game_time="12:00 PM")
    minds.relationships.record_visit("maya", tick=5, game_day=3, game_time="01:00 PM")

    panel = minds.memory_panel_lines("maya")
    assert panel
    assert len(rel.facts) >= 4
    assert rel.visit_count >= 2
    assert rel.opinion


def test_greeting_differs_trust_vs_thief():
    from nyc_world.simulation.relationships import NPCPlayerRelationship

    thief = NPCPlayerRelationship(npc_id="maya")
    thief.facts.append(
        make_fact("stole", "You stole her coffee", tick=1, game_day=1, game_time="09:00 AM", sentiment=-0.9)
    )
    friend = NPCPlayerRelationship(npc_id="maya", trust=70, friendship=55, visit_count=3)

    thief_key = pick_npc_greeting("maya", thief, quest_active_id=None, quest_completed=set())
    friend_key = pick_npc_greeting(
        "maya", friend, quest_active_id=None, quest_completed={"missing_camera"}
    )
    assert thief_key == "maya_hostile"
    assert friend_key in ("maya_friendly", "maya_hoping_you_come_by", "maya_returning")


def test_save_load_restores_memories(tmp_path: Path, projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=2, vehicle_count=0)
    minds = city.mind_registry
    minds.relationships.record_fact(
        "maya", "helped", "Found camera", tick=1, game_day=1, game_time="08:00 AM",
    )
    opinion_before = minds.relationships.get("maya").opinion

    save = capture_save(
        player=PlayerProfile(),
        relationships=minds.relationships,
        minds=minds,
        quests=QuestManager(PlayerProfile(), minds=minds),
        event_log=EventLog(),
        tick=5,
        game_day=1,
        player_x=1,
        player_z=2,
        clock_hour=8,
        clock_minute=0,
        clock_weather="clear",
    )
    path = tmp_path / "mem.json"
    save.write(path)

    city2 = CitySimulation(projection, 50.0, 50.0, npc_count=2, vehicle_count=0)
    from nyc_world.game.save import GameSave

    apply_save(
        GameSave.load(path),
        player=PlayerProfile(),
        relationships=city2.mind_registry.relationships,
        minds=city2.mind_registry,
        quests=QuestManager(PlayerProfile(), minds=city2.mind_registry),
        event_log=EventLog(),
        city=city2,
    )
    rel = city2.mind_registry.relationships.get("maya")
    assert rel.facts
    assert rel.opinion == opinion_before


def test_world_state_includes_relationship_summary(projection: GeoProjection):
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
    maya_rel = next((r for r in state.relationships if r.npc_id == "maya"), None)
    assert maya_rel is not None
    assert maya_rel.visit_count >= 1
    assert maya_rel.opinion


def test_opinion_synthesis_golden_strings():
    helpful = synthesize_opinion(
        75, 55,
        [make_fact("helped", "helped", tick=1, game_day=1, game_time="08:00")],
    )
    assert "helpful" in helpful.lower()
    thief = synthesize_opinion(
        40, 30,
        [make_fact("stole", "stole", tick=1, game_day=1, game_time="08:00", sentiment=-0.9)],
    )
    assert "suspicious" in thief.lower() or "distance" in thief.lower()

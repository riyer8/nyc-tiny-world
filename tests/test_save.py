"""Tests for game save/load."""

from pathlib import Path

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.game.save import apply_save, capture_save, GameSave
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.npc_mind import NPCMindRegistry
import pytest


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_save_load_roundtrip(tmp_path: Path, projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0)
    player = PlayerProfile(money=50)
    minds = city.mind_registry
    quests = QuestManager(player, minds=minds)
    event_log = EventLog()
    minds.on_player_stole("maya", "coffee")
    minds.set_time_context(tick=42, game_day=2, game_time="10:00 AM")

    save = capture_save(
        player=player,
        relationships=minds.relationships,
        minds=minds,
        quests=quests,
        event_log=event_log,
        tick=42,
        game_day=2,
        player_x=123.0,
        player_z=456.0,
        clock_hour=10,
        clock_minute=30,
        clock_weather="clear",
    )
    path = tmp_path / "test.json"
    save.write(path)

    player2 = PlayerProfile()
    minds2 = NPCMindRegistry()
    minds2.register_quest_npcs()
    quests2 = QuestManager(player2, minds=minds2)
    event_log2 = EventLog()
    city2 = CitySimulation(projection, 0.0, 0.0, mind_registry=minds2)

    loaded = GameSave.load(path)
    px, pz = apply_save(
        loaded,
        player=player2,
        relationships=minds2.relationships,
        minds=minds2,
        quests=quests2,
        event_log=event_log2,
        city=city2,
    )

    assert px == 123.0
    assert pz == 456.0
    assert minds2.relationships.get("maya").has_fact("stole")
    assert city2.clock.hour == 10
    assert city2.clock.day == 2

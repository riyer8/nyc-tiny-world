"""Tests for public NPC mod API."""

from __future__ import annotations

from pathlib import Path

import pytest

from nyc_world.agents import NPC, NPCRegistry, Needs, Personality, Schedule, load_mods
from nyc_world.agents.registry import resolve_location
from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation.adapters import capture_world_state
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_register_npc_spawns_in_city(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    before = len(city.npcs)
    npc = NPC(
        id="mod_river",
        name="River",
        personality=Personality(curiosity=0.9),
        schedule=Schedule.workplace("cafe_village", hour=10),
    )
    city.register_npc(npc)
    assert len(city.npcs) == before + 1
    assert city.agent_controller.get("mod_river") is not None


def test_load_mod_file(tmp_path: Path, projection: GeoProjection):
    mod = tmp_path / "test_npc.py"
    mod.write_text(
        '''
from nyc_world.agents import NPC, Personality, Schedule

def register(registry):
    registry.register(NPC(
        id="mod_sam",
        name="Sam",
        personality=Personality(kindness=0.8),
        schedule=Schedule.workplace("photo_shop"),
        dialogue_pack="sam_default",
    ))
'''
    )
    registry = load_mods(mods_dir=tmp_path)
    assert any(n.id == "mod_sam" for n in registry.all())


def test_mod_npc_serializes_to_world_state(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=2, vehicle_count=0)
    city.register_npc(
        NPC(id="mod_taylor", name="Taylor", schedule=Schedule.workplace("library_building"))
    )
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    state = capture_world_state(
        city,
        player,
        quests,
        city.mind_registry,
        tick=1,
        player_x=100,
        player_z=100,
    )
    ids = {n.id for n in state.npcs}
    assert "mod_taylor" in ids


def test_resolve_location_offset(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=0, vehicle_count=0)
    x, z = resolve_location(city, "cafe_village")
    assert x != 0 or z != 0


def test_registry_roundtrip():
    registry = NPCRegistry()
    registry.register(
        NPC(
            id="a",
            name="A",
            personality=Personality(curiosity=0.5),
            needs=Needs(money=0.3),
            schedule=Schedule.workplace("cafe_village"),
        )
    )
    restored = NPCRegistry.from_dict(registry.to_dict())
    assert restored.all()[0].id == "a"

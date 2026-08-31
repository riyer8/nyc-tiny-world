"""Tests for city economy and weekly evolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.game.interactables import Interactable, InteractableKind
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.game.save import apply_save, capture_save
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation import Simulation
from nyc_world.simulation.economy import Business, CityEconomy, seed_village_economy
from nyc_world.simulation.event_log import EventLog


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_weekly_tick_accounting():
    economy = seed_village_economy()
    assert len(economy.businesses) >= 10
    joes = economy.businesses["joes_camera"]
    start_cash = joes.cash
    economy.weekly_tick(rng=__import__("random").Random(1))
    assert joes.cash != start_cash or economy.journal


def test_bankruptcy_spawns_replacement():
    economy = seed_village_economy()
    biz = economy.businesses["joes_camera"]
    biz.cash = -50.0
    biz.base_revenue = 5.0
    lines = economy.weekly_tick(rng=__import__("random").Random(7))
    assert any("closed" in line.lower() for line in lines)
    assert any("opened" in line.lower() for line in lines)
    replacement = economy.business_at_location("photo_shop")
    assert replacement is not None
    assert replacement.name != "Joe's Camera"
    assert replacement.open


def test_facade_label_updates():
    economy = seed_village_economy()
    item = Interactable(
        id="photo_shop",
        kind=InteractableKind.BUILDING,
        x=0,
        z=0,
        label="Photo Shop",
    )
    economy.apply_facades([item])
    assert item.label == "Joe's Camera"
    economy.businesses["joes_camera"].open = False
    economy.businesses["photo_shop_0"] = Business(
        id="photo_shop_0",
        name="Lens & Leaf",
        location_id="photo_shop",
        cash=100,
        reputation=0.6,
        staff=[],
    )
    economy.apply_facades([item])
    assert item.label == "Lens & Leaf"


def test_seven_day_fast_forward_changes_state(projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    city.economy.businesses["joes_camera"].cash = 10.0
    city.economy.businesses["joes_camera"].base_revenue = 8.0
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    sim = Simulation(city, player, quests, minds=city.mind_registry, event_log=EventLog())

    start_day = city.clock.day
    for _ in range(3600):
        sim.advance_world(1.0, speed_multiplier=30.0, time_scale=30.0)
        if city.clock.day >= start_day + 7:
            break

    assert city.clock.day >= start_day + 7
    assert city.economy.journal, "expected at least one evolution entry after a week"


def test_economy_save_roundtrip(tmp_path: Path, projection: GeoProjection):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=2, vehicle_count=0)
    city.economy.weekly_tick()
    city.economy.businesses["joes_camera"].cash = -99

    save = capture_save(
        player=PlayerProfile(),
        relationships=city.mind_registry.relationships,
        minds=city.mind_registry,
        quests=QuestManager(PlayerProfile(), minds=city.mind_registry),
        event_log=EventLog(),
        tick=10,
        game_day=city.clock.day,
        player_x=1.0,
        player_z=2.0,
        clock_hour=city.clock.hour,
        clock_minute=city.clock.minute,
        clock_weather=city.clock.weather.value,
        economy=city.economy.to_dict(),
    )
    path = tmp_path / "eco.json"
    save.write(path)

    city2 = CitySimulation(projection, 50.0, 50.0, npc_count=2, vehicle_count=0)
    loaded = __import__("nyc_world.game.save", fromlist=["GameSave"]).GameSave.load(path)
    apply_save(
        loaded,
        player=PlayerProfile(),
        relationships=city2.mind_registry.relationships,
        minds=city2.mind_registry,
        quests=QuestManager(PlayerProfile(), minds=city2.mind_registry),
        event_log=EventLog(),
        city=city2,
    )
    assert city2.economy.week == city.economy.week
    assert len(city2.economy.journal) == len(city.economy.journal)
    assert city2.economy.businesses["joes_camera"].cash == -99


def test_for_rent_facade_suffix():
    economy = CityEconomy()
    economy.residences["unit"] = __import__(
        "nyc_world.simulation.economy", fromlist=["Residence"]
    ).Residence(
        unit_id="unit",
        location_id="library_building",
        occupants=[],
        rent=1500,
        for_rent=True,
    )
    label = economy.facade_label("library_building", "Jefferson Market Library")
    assert "FOR RENT" in label

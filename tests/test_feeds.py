"""Tests for NYC live feeds and simulation effects."""

from pathlib import Path

import pytest

from nyc_world.city.world_clock import Weather, WorldClock
from nyc_world.core.projection import GeoProjection
from nyc_world.feeds import FeedManager, modifiers_from_feed
from nyc_world.feeds.effects import apply_score_modifiers, count_transit_affected_npcs
from nyc_world.feeds.parsers import parse_feed_bundle, parse_mta_alerts, parse_open_meteo
from nyc_world.paths import DEFAULT_META_PATH

FIXTURE = Path(__file__).parent / "fixtures" / "feeds" / "mta_delay.json"


def test_parse_feed_fixture():
    data = FIXTURE.read_text()
    import json

    state = parse_feed_bundle(json.loads(data))
    assert state.weather is not None
    assert state.weather.condition == "rain"
    assert len(state.transit) == 1
    assert state.transit[0].line == "F"
    assert state.transit[0].delay_minutes == 15


def test_modifiers_from_transit_delay():
    import json

    state = parse_feed_bundle(json.loads(FIXTURE.read_text()))
    mods = modifiers_from_feed(state)
    assert mods.weather_override == "rain"
    assert mods.subway_boarding_rate < 1.0
    assert mods.bus_route_weight > 1.0
    assert mods.sidewalk_density_near_station > 0
    assert mods.cafe_occupancy_boost > 0
    assert mods.umbrella_probability > 0


def test_apply_score_modifiers_near_subway():
    import json

    mods = modifiers_from_feed(parse_feed_bundle(json.loads(FIXTURE.read_text())))
    base = {"wander": 0.2, "explore": 0.5, "socialize": 0.3}
    boosted = apply_score_modifiers(base, mods, near_subway=True, near_cafe=False)
    assert boosted["wander"] > base["wander"]
    assert boosted["explore"] < base["explore"]


def test_feed_manager_offline_is_inert(tmp_path: Path):
    mgr = FeedManager(offline=True, cache_dir=tmp_path)
    state = mgr.poll(force=True)
    assert state.source == "offline"
    assert mgr.modifiers.subway_boarding_rate == 1.0
    assert mgr.hud_banner() == []


def test_feed_manager_applies_weather_override(tmp_path: Path):
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    from nyc_world.city.city_sim import CitySimulation

    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    mgr = FeedManager(offline=True, cache_dir=tmp_path)
    mgr.load_from_file(FIXTURE)
    mods = mgr.apply_to_sim(city)
    assert city.clock.weather == Weather.RAIN
    assert mods.subway_boarding_rate < 1.0


def test_weather_feed_locks_procedural_changes():
    clock = WorldClock()
    clock.set_feed_weather(Weather.RAIN)
    clock.advance(200.0)
    assert clock.weather == Weather.RAIN
    clock.clear_feed_weather()
    clock.advance(200.0)
    assert clock.weather in {Weather.CLEAR, Weather.CLOUDY, Weather.RAIN, Weather.FOG}


def test_parse_open_meteo_rain_code():
    data = {"current": {"weather_code": 61}}
    alert = parse_open_meteo(data)
    assert alert is not None
    assert alert.condition == "rain"


def test_parse_mta_alerts():
    alerts = parse_mta_alerts(
        {"alerts": [{"line": "F", "delay_minutes": 20, "summary": "Signal problems"}]}
    )
    assert len(alerts) == 1
    assert alerts[0].delay_minutes == 20


def test_transit_affected_npc_count():
    import json

    mods = modifiers_from_feed(parse_feed_bundle(json.loads(FIXTURE.read_text())))
    positions = {"a": (0.0, 0.0), "b": (100.0, 100.0)}
    subways = [(5.0, 5.0)]
    count = count_transit_affected_npcs(positions, subways, mods, radius_m=50.0)
    assert count == 1

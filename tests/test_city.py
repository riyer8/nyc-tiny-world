"""Tests for landmarks and city simulation."""

import pytest

from nyc_world.city_sim import CitySimulation
from nyc_world.landmarks import CAFE, LANDMARK, STORE, load_landmarks_for_area
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.projection import GeoProjection
from nyc_world.world_clock import Weather, WorldClock


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_landmarks_load(projection: GeoProjection) -> None:
    landmarks = load_landmarks_for_area(projection)
    assert len(landmarks) > 10
    kinds = {lm.kind for lm in landmarks}
    assert LANDMARK in kinds or STORE in kinds or CAFE in kinds


def test_world_clock_advances() -> None:
    clock = WorldClock(hour=8, minute=0, speed=60)
    clock.advance(1.0)
    assert clock.hour == 9
    assert clock.minute == 0


def test_weather_affects_brightness() -> None:
    clear = WorldClock(weather=Weather.CLEAR)
    rain = WorldClock(weather=Weather.RAIN)
    assert rain.ambient_brightness() < clear.ambient_brightness()


def test_city_simulation(projection: GeoProjection) -> None:
    city = CitySimulation(projection, 500, 500, npc_count=8, vehicle_count=6)
    assert len(city.landmarks) > 0
    assert len(city.npcs) == 8
    assert len(city.vehicles) == 6
    city.update(1.0)
    assert city.clock.minute > 0 or city.clock.hour > 8

"""Tests for geographic projection."""

from nyc_world.areas import GREENWICH_VILLAGE
from nyc_world.projection import GeoProjection


def test_round_trip() -> None:
    proj = GeoProjection.from_area(GREENWICH_VILLAGE, cols=80, rows=80, tile_size=16)
    lat, lon = 40.73061, -73.9973
    x, y = proj.to_game(lat, lon)
    lat2, lon2 = proj.to_gps(x, y)
    assert abs(lat2 - lat) < 1e-6
    assert abs(lon2 - lon) < 1e-6


def test_east_increases_longitude() -> None:
    proj = GeoProjection.from_area(GREENWICH_VILLAGE, cols=80, rows=80, tile_size=16)
    lat, lon = GREENWICH_VILLAGE.spawn_lat, GREENWICH_VILLAGE.spawn_lon
    x0, y0 = proj.to_game(lat, lon)
    _, lon_east = proj.to_gps(x0 + 50, y0)
    _, lon_west = proj.to_gps(x0 - 50, y0)
    assert lon_east > lon
    assert lon_west < lon


def test_north_decreases_y() -> None:
    proj = GeoProjection.from_area(GREENWICH_VILLAGE, cols=80, rows=80, tile_size=16)
    lat, lon = GREENWICH_VILLAGE.spawn_lat, GREENWICH_VILLAGE.spawn_lon
    x0, y0 = proj.to_game(lat, lon)
    lat_north, _ = proj.to_gps(x0, y0 - 50)
    lat_south, _ = proj.to_gps(x0, y0 + 50)
    assert lat_north > lat
    assert lat_south < lat

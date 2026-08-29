"""Geographic tile grid for streaming OSM data."""

from __future__ import annotations

import math
from dataclasses import dataclass

from nyc_world.geo.regions import MANHATTAN

METERS_PER_DEGREE_LAT = 111_320.0
TILE_SIZE_M = 500.0

# Manhattan southwest corner anchors the tile grid.
ORIGIN_LAT = MANHATTAN.south
ORIGIN_LON = MANHATTAN.west


@dataclass(frozen=True)
class GeoTile:
    row: int
    col: int

    @property
    def tile_id(self) -> str:
        return f"{self.row}_{self.col}"


def meters_per_degree_lon(lat: float) -> float:
    return METERS_PER_DEGREE_LAT * math.cos(math.radians(lat))


def _meters_per_degree_lon(lat: float) -> float:
    return meters_per_degree_lon(lat)


def gps_to_meters(lat: float, lon: float) -> tuple[float, float]:
    """Meters east/north from the Manhattan grid origin."""
    east = (lon - ORIGIN_LON) * _meters_per_degree_lon(ORIGIN_LAT)
    north = (lat - ORIGIN_LAT) * METERS_PER_DEGREE_LAT
    return east, north


def meters_to_gps(east: float, north: float) -> tuple[float, float]:
    lat = ORIGIN_LAT + north / METERS_PER_DEGREE_LAT
    lon = ORIGIN_LON + east / _meters_per_degree_lon(ORIGIN_LAT)
    return lat, lon


def gps_to_tile(lat: float, lon: float) -> GeoTile:
    east, north = gps_to_meters(lat, lon)
    col = int(math.floor(east / TILE_SIZE_M))
    row = int(math.floor(north / TILE_SIZE_M))
    return GeoTile(row=row, col=col)


def tile_center_gps(tile: GeoTile) -> tuple[float, float]:
    east = (tile.col + 0.5) * TILE_SIZE_M
    north = (tile.row + 0.5) * TILE_SIZE_M
    return meters_to_gps(east, north)


def tile_bbox(tile: GeoTile) -> tuple[float, float, float, float]:
    """Return (south, west, north, east) for a tile."""
    south_west_lat, south_west_lon = meters_to_gps(
        tile.col * TILE_SIZE_M,
        tile.row * TILE_SIZE_M,
    )
    north_east_lat, north_east_lon = meters_to_gps(
        (tile.col + 1) * TILE_SIZE_M,
        (tile.row + 1) * TILE_SIZE_M,
    )
    south = min(south_west_lat, north_east_lat)
    north = max(south_west_lat, north_east_lat)
    west = min(south_west_lon, north_east_lon)
    east = max(south_west_lon, north_east_lon)
    return south, west, north, east


def tiles_within_radius(lat: float, lon: float, radius_m: float) -> list[GeoTile]:
    """All tile IDs whose centers are within radius_m of the player."""
    center = gps_to_tile(lat, lon)
    tile_radius = int(math.ceil(radius_m / TILE_SIZE_M)) + 1
    tiles: list[GeoTile] = []
    for dr in range(-tile_radius, tile_radius + 1):
        for dc in range(-tile_radius, tile_radius + 1):
            tile = GeoTile(row=center.row + dr, col=center.col + dc)
            t_lat, t_lon = tile_center_gps(tile)
            east, north = gps_to_meters(lat, lon)
            te, tn = gps_to_meters(t_lat, t_lon)
            if math.hypot(te - east, tn - north) <= radius_m + TILE_SIZE_M * 0.75:
                tiles.append(tile)
    return tiles

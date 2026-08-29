"""Geographic coordinate transforms — single source of truth."""

from __future__ import annotations

from nyc_world.core.projection import GeoProjection


def lonlat_to_world_xz(projection: GeoProjection, lon: float, lat: float) -> tuple[float, float]:
    """GPS → 3D world meters (x=east, z=north)."""
    game_x, game_y = projection.to_game(lat, lon)
    mpt = projection.meters_per_tile()
    x = game_x / projection.tile_size * mpt
    row = game_y / projection.tile_size
    z = (projection.rows - row) * mpt
    return x, z


def world_xz_to_game_px(
    x: float,
    z: float,
    projection: GeoProjection,
    meters_per_tile: float,
) -> tuple[float, float]:
    """3D world meters → game pixel coordinates."""
    game_x = x / meters_per_tile * projection.tile_size
    game_y = (projection.rows - z / meters_per_tile) * projection.tile_size
    return game_x, game_y


def game_px_to_world_xz(
    game_x: float,
    game_y: float,
    projection: GeoProjection,
    meters_per_tile: float,
) -> tuple[float, float]:
    """Game pixel coordinates → 3D world meters."""
    x = game_x / projection.tile_size * meters_per_tile
    row = game_y / projection.tile_size
    z = (projection.rows - row) * meters_per_tile
    return x, z


def world_xz_to_gps(
    x: float,
    z: float,
    projection: GeoProjection,
    meters_per_tile: float,
) -> tuple[float, float]:
    """3D world position → (latitude, longitude)."""
    game_x, game_y = world_xz_to_game_px(x, z, projection, meters_per_tile)
    return projection.to_gps(game_x, game_y)


def gps_to_world_xz(
    lat: float,
    lon: float,
    projection: GeoProjection,
) -> tuple[float, float]:
    """(latitude, longitude) → 3D world meters."""
    return lonlat_to_world_xz(projection, lon, lat)

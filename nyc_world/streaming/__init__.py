"""Streaming world — tile-based OSM loading with LOD radii."""

from nyc_world.streaming.loader import TileDataLoader
from nyc_world.streaming.lod import lod_buildings, lod_landmarks, lod_npcs, lod_vehicles
from nyc_world.streaming.radii import DEFAULT_RADII, METERS_PER_MILE, StreamRadii
from nyc_world.streaming.tiles import GeoTile, TILE_SIZE_M, gps_to_tile, tile_bbox, tiles_within_radius
from nyc_world.streaming.state import StreamingState
from nyc_world.streaming.world_manager import StreamingWorldManager

__all__ = [
    "DEFAULT_RADII",
    "GeoTile",
    "METERS_PER_MILE",
    "StreamRadii",
    "StreamingState",
    "StreamingWorldManager",
    "TileDataLoader",
    "TILE_SIZE_M",
    "gps_to_tile",
    "lod_buildings",
    "lod_landmarks",
    "lod_npcs",
    "lod_vehicles",
    "tile_bbox",
    "tiles_within_radius",
]

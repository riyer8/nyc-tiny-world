"""OSM data loading and map generation."""

from nyc_world.map.buildings import Building3D, load_buildings_for_area
from nyc_world.map.map_generator import generate_map

__all__ = ["Building3D", "fetch_osm", "generate_map", "load_buildings_for_area"]


def __getattr__(name: str):
    if name == "fetch_osm":
        from nyc_world.map.osm_fetch import fetch_osm

        return fetch_osm
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

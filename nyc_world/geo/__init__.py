"""Geographic grounding — coordinates, context, and mini-map."""

from nyc_world.geo.coords import (
    game_px_to_world_xz,
    gps_to_world_xz,
    lonlat_to_world_xz,
    world_xz_to_game_px,
    world_xz_to_gps,
)
from nyc_world.geo.regions import BROOKLYN, MANHATTAN, NYC, GeoRegion

__all__ = [
    "BROOKLYN",
    "GeoRegion",
    "MANHATTAN",
    "MinimapState",
    "NYC",
    "PlayerLocation",
    "build_minimap",
    "game_px_to_world_xz",
    "gps_to_world_xz",
    "locate_player",
    "lonlat_to_world_xz",
    "world_xz_to_game_px",
    "world_xz_to_gps",
]


def __getattr__(name: str):
    if name in ("PlayerLocation", "locate_player"):
        from nyc_world.geo.context import PlayerLocation, locate_player

        return {"PlayerLocation": PlayerLocation, "locate_player": locate_player}[name]
    if name in ("MinimapState", "build_minimap"):
        from nyc_world.geo.minimap import MinimapState, build_minimap

        return {"MinimapState": MinimapState, "build_minimap": build_minimap}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

"""Core world model: map tiles, projection, and 3D scene."""

from nyc_world.core.areas import AREAS, GREENWICH_VILLAGE, Area
from nyc_world.core.projection import GeoProjection
from nyc_world.core.world import World
from nyc_world.core.world_3d import EYE_HEIGHT, Box3D, World3D

__all__ = [
    "AREAS",
    "Area",
    "Box3D",
    "EYE_HEIGHT",
    "GREENWICH_VILLAGE",
    "GeoProjection",
    "World",
    "World3D",
]

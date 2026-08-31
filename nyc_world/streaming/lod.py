"""Level-of-detail filtering for streamed world content."""

from __future__ import annotations

import math
from typing import TypeVar

from nyc_world.map.buildings import Building3D
from nyc_world.city.landmarks import Landmark3D
from nyc_world.city.npcs import NPC
from nyc_world.city.vehicles import Vehicle
from nyc_world.streaming.radii import StreamRadii

T = TypeVar("T")


def distance_xz(x0: float, z0: float, x1: float, z1: float) -> float:
    return math.hypot(x1 - x0, z1 - z1)


def building_center(building: Building3D) -> tuple[float, float]:
    xs = [p[0] for p in building.footprint]
    zs = [p[1] for p in building.footprint]
    return sum(xs) / len(xs), sum(zs) / len(zs)


def within_radius_xz(
    items: list[T],
    player_x: float,
    player_z: float,
    radius_m: float,
    position_fn,
) -> list[T]:
    out: list[T] = []
    for item in items:
        ix, iz = position_fn(item)
        if distance_xz(player_x, player_z, ix, iz) <= radius_m:
            out.append(item)
    return out


def lod_buildings(
    buildings: list[Building3D],
    player_x: float,
    player_z: float,
    radii: StreamRadii,
) -> tuple[list[Building3D], list[Building3D]]:
    """Return (near detailed 3D buildings, far skyline impostors)."""
    detailed: list[Building3D] = []
    far: list[Building3D] = []
    for building in buildings:
        cx, cz = building_center(building)
        dist = distance_xz(player_x, player_z, cx, cz)
        if dist <= radii.render_3d_m:
            detailed.append(building)
        elif dist <= radii.data_m:
            far.append(building)
    return detailed, far


def lod_landmarks(
    landmarks: list[Landmark3D],
    player_x: float,
    player_z: float,
    radius_m: float,
) -> list[Landmark3D]:
    return within_radius_xz(
        landmarks, player_x, player_z, radius_m, lambda lm: (lm.x, lm.z)
    )


def lod_npcs(npcs: list[NPC], player_x: float, player_z: float, radius_m: float) -> list[NPC]:
    return within_radius_xz(npcs, player_x, player_z, radius_m, lambda n: (n.x, n.z))


def lod_vehicles(
    vehicles: list[Vehicle], player_x: float, player_z: float, radius_m: float
) -> list[Vehicle]:
    return within_radius_xz(
        vehicles, player_x, player_z, radius_m, lambda v: (v.x, v.z)
    )

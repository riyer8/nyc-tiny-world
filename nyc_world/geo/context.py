"""Geographic context: nearest street, POI, and player location."""

from __future__ import annotations

import math
from dataclasses import dataclass

from nyc_world.city.landmarks import Landmark3D
from nyc_world.city.streets import NamedStreetSegment, StreetNetwork
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import world_xz_to_gps


@dataclass(frozen=True)
class PlayerLocation:
    latitude: float
    longitude: float
    neighborhood: str
    nearest_street: str
    street_distance_m: float
    nearest_poi: str
    poi_distance_m: float
    borough: str


def _point_segment_distance(
    px: float,
    pz: float,
    x0: float,
    z0: float,
    x1: float,
    z1: float,
) -> float:
    dx, dz = x1 - x0, z1 - z0
    length_sq = dx * dx + dz * dz
    if length_sq < 1e-6:
        return math.hypot(px - x0, pz - z0)
    t = max(0.0, min(1.0, ((px - x0) * dx + (pz - z0) * dz) / length_sq))
    proj_x = x0 + t * dx
    proj_z = z0 + t * dz
    return math.hypot(px - proj_x, pz - proj_z)


def nearest_named_street(
    streets: StreetNetwork | None,
    x: float,
    z: float,
    *,
    max_distance: float = 40.0,
) -> tuple[str, float]:
    if not streets or not streets.named_segments:
        return "Unknown", float("inf")
    best_name = "Unknown"
    best_dist = float("inf")
    for segment in streets.named_segments:
        dist = _point_segment_distance(x, z, segment.x0, segment.z0, segment.x1, segment.z1)
        if dist < best_dist:
            best_dist = dist
            best_name = segment.name
    if best_dist > max_distance:
        return "Unknown", best_dist
    return best_name, best_dist


def nearest_poi(
    landmarks: list[Landmark3D],
    x: float,
    z: float,
    *,
    max_distance: float = 80.0,
) -> tuple[str, float]:
    if not landmarks:
        return "None nearby", float("inf")
    best_name = "None nearby"
    best_dist = float("inf")
    for lm in landmarks:
        if not lm.name:
            continue
        dist = math.hypot(lm.x - x, lm.z - z)
        if dist < best_dist:
            best_dist = dist
            best_name = lm.name
    if best_dist > max_distance:
        return "None nearby", best_dist
    return best_name, best_dist


def borough_for(lat: float, lon: float) -> str:
    from nyc_world.geo.regions import BROOKLYN, MANHATTAN

    if MANHATTAN.contains(lat, lon):
        return "Manhattan"
    if BROOKLYN.contains(lat, lon):
        return "Brooklyn"
    return "NYC"


def locate_player(
    projection: GeoProjection,
    meters_per_tile: float,
    x: float,
    z: float,
    streets: StreetNetwork | None,
    landmarks: list[Landmark3D],
) -> PlayerLocation:
    lat, lon = world_xz_to_gps(x, z, projection, meters_per_tile)
    street, street_dist = nearest_named_street(streets, x, z)
    poi, poi_dist = nearest_poi(landmarks, x, z)
    return PlayerLocation(
        latitude=lat,
        longitude=lon,
        neighborhood=projection.area_name or "Unknown",
        nearest_street=street,
        street_distance_m=street_dist,
        nearest_poi=poi,
        poi_distance_m=poi_dist,
        borough=borough_for(lat, lon),
    )

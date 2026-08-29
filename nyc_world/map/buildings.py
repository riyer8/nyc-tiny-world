"""Load real building footprints from OSM and estimate heights."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from shapely.geometry import LineString, Polygon

from nyc_world.core.projection import GeoProjection
from nyc_world.map.map_generator import OsmIndex
from nyc_world.paths import DATA_DIR

METERS_PER_STORY = 3.5
MIN_HEIGHT = 3.0
MAX_HEIGHT = 280.0

# Default story count when OSM has no height/levels tag.
DEFAULT_STORIES: dict[str, int] = {
    "house": 2,
    "detached": 2,
    "terrace": 3,
    "retail": 2,
    "commercial": 4,
    "apartments": 6,
    "residential": 5,
    "office": 12,
    "university": 8,
    "dormitory": 8,
    "church": 2,
    "school": 3,
    "public": 4,
    "warehouse": 2,
    "garage": 1,
    "industrial": 2,
    "hotel": 10,
    "hospital": 6,
    "yes": 4,
}


@dataclass(frozen=True)
class Building3D:
    """Extruded building: footprint ring in world x/z + height in meters."""

    footprint: tuple[tuple[float, float], ...]
    height: float
    wall_r: float
    wall_g: float
    wall_b: float
    roof_r: float
    roof_g: float
    roof_b: float
    name: str = ""


def lonlat_to_world_xz(projection: GeoProjection, lon: float, lat: float) -> tuple[float, float]:
    game_x, game_y = projection.to_game(lat, lon)
    mpt = projection.meters_per_tile()
    x = game_x / projection.tile_size * mpt
    row = game_y / projection.tile_size
    z = (projection.rows - row) * mpt
    return x, z


def parse_meters(value: str) -> float:
    text = value.strip().lower().replace(",", ".")
    if text.endswith("ft") or text.endswith("'"):
        feet = float(re.sub(r"[^\d.]", "", text))
        return feet * 0.3048
    return float(re.sub(r"[^\d.]", "", text))


def estimate_height_m(tags: dict) -> float:
    """Estimate building height from OSM tags (meters)."""
    if "height" in tags:
        try:
            return max(MIN_HEIGHT, min(MAX_HEIGHT, parse_meters(tags["height"])))
        except ValueError:
            pass

    for key in ("building:levels", "levels"):
        if key in tags:
            raw = tags[key].split(";")[0].split(",")[0]
            try:
                stories = float(raw)
                return max(MIN_HEIGHT, min(MAX_HEIGHT, stories * METERS_PER_STORY))
            except ValueError:
                pass

    building_type = tags.get("building", "yes")
    stories = DEFAULT_STORIES.get(building_type, DEFAULT_STORIES["yes"])
    return stories * METERS_PER_STORY


def height_colors(height: float) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """Return (wall_rgb, roof_rgb) — short / medium / skyscraper."""
    if height < 12:  # ~1–3 stories
        wall = (0.58, 0.60, 0.64)
        roof = (0.66, 0.68, 0.72)
    elif height < 45:  # ~4–12 stories
        wall = (0.32, 0.37, 0.51)
        roof = (0.40, 0.45, 0.58)
    else:  # skyscraper
        wall = (0.20, 0.26, 0.42)
        roof = (0.28, 0.34, 0.50)
    return wall, roof


def _relation_polygons(index: OsmIndex, relation: dict) -> list[Polygon]:
    outers: list[LineString] = []
    inners: list[LineString] = []

    for member in relation.get("members", []):
        if member.get("type") != "way":
            continue
        way = index.ways.get(member["ref"])
        if not way:
            continue
        coords = [
            index.nodes[nid]
            for nid in way.get("nodes", [])
            if nid in index.nodes
        ]
        if len(coords) < 2:
            continue
        line = LineString(coords)
        if member.get("role") == "inner":
            inners.append(line)
        else:
            outers.append(line)

    polygons: list[Polygon] = []
    for outer in outers:
        if not outer.is_closed:
            coords = list(outer.coords)
            if coords[0] != coords[-1]:
                coords.append(coords[0])
            outer = LineString(coords)
        try:
            poly = Polygon(outer)
            for inner in inners:
                if inner.is_closed:
                    poly = poly.difference(Polygon(inner))
            if poly.is_valid and not poly.is_empty:
                if poly.geom_type == "Polygon":
                    polygons.append(poly)
                elif poly.geom_type == "MultiPolygon":
                    polygons.extend(poly.geoms)
        except Exception:
            continue
    return polygons


def _polygon_to_building(
    polygon: Polygon,
    tags: dict,
    projection: GeoProjection,
) -> Building3D | None:
    if polygon.is_empty or not polygon.is_valid:
        return None

    ring = list(polygon.exterior.coords)[:-1]
    if len(ring) < 3:
        return None

    footprint = tuple(lonlat_to_world_xz(projection, lon, lat) for lon, lat in ring)
    height = estimate_height_m(tags)
    wall, roof = height_colors(height)
    name = tags.get("name", "")

    return Building3D(
        footprint=footprint,
        height=height,
        wall_r=wall[0],
        wall_g=wall[1],
        wall_b=wall[2],
        roof_r=roof[0],
        roof_g=roof[1],
        roof_b=roof[2],
        name=name,
    )


def load_buildings(projection: GeoProjection, osm_data: dict) -> list[Building3D]:
    index = OsmIndex.from_osm(osm_data)
    buildings: list[Building3D] = []

    for way in index.ways.values():
        if "building" not in way.get("tags", {}):
            continue
        coords = [
            index.nodes[nid]
            for nid in way.get("nodes", [])
            if nid in index.nodes
        ]
        if len(coords) < 3:
            continue
        try:
            poly = Polygon(coords)
            if not poly.is_valid:
                poly = poly.buffer(0)
            building = _polygon_to_building(poly, way["tags"], projection)
            if building:
                buildings.append(building)
        except Exception:
            continue

    for relation in index.relations.values():
        if "building" not in relation.get("tags", {}):
            continue
        for poly in _relation_polygons(index, relation):
            building = _polygon_to_building(poly, relation["tags"], projection)
            if building:
                buildings.append(building)

    return buildings


def load_buildings_for_area(projection: GeoProjection) -> list[Building3D]:
    slug = projection.area_slug or "greenwich_village"
    path = DATA_DIR / f"{slug}_osm.json"
    if not path.exists():
        return []
    osm_data = json.loads(path.read_text())
    return load_buildings(projection, osm_data)

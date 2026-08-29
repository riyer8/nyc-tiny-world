"""Recognizable landmarks and POIs from OpenStreetMap."""

from __future__ import annotations

import json
from dataclasses import dataclass
from nyc_world.map.buildings import lonlat_to_world_xz
from nyc_world.map.map_generator import OsmIndex
from nyc_world.paths import DATA_DIR
from nyc_world.core.projection import GeoProjection

CAFE = "cafe"
SUBWAY = "subway"
PARK = "park"
STORE = "store"
LANDMARK = "landmark"


@dataclass(frozen=True)
class Landmark3D:
    kind: str
    x: float
    z: float
    name: str
    height: float = 3.0


def _classify(tags: dict) -> str | None:
    amenity = tags.get("amenity", "")
    shop = tags.get("shop", "")
    tourism = tags.get("tourism", "")
    railway = tags.get("railway", "")
    leisure = tags.get("leisure", "")
    historic = tags.get("historic", "")

    if railway in ("station", "subway_entrance") or amenity == "subway_entrance":
        return SUBWAY
    if tags.get("entrance") == "yes" and tags.get("subway") == "yes":
        return SUBWAY
    if amenity in ("cafe", "coffee_shop", "bakery") or tags.get("cuisine") == "coffee":
        return CAFE
    if leisure in ("park", "garden") and tags.get("name"):
        return PARK
    if shop or amenity in ("restaurant", "fast_food", "bar", "pub"):
        return STORE
    if tourism in ("attraction", "museum", "artwork", "viewpoint") or historic:
        return LANDMARK
    if tags.get("wikidata") or tags.get("name") and amenity in (
        "university",
        "library",
        "theatre",
        "place_of_worship",
    ):
        return LANDMARK
    return None


def load_landmarks(projection: GeoProjection, osm_data: dict) -> list[Landmark3D]:
    index = OsmIndex.from_osm(osm_data)
    landmarks: list[Landmark3D] = []
    seen: set[tuple[str, int]] = set()

    def add(kind: str, x: float, z: float, name: str, height: float = 3.0) -> None:
        key = (kind, int(x), int(z))
        if key in seen:
            return
        seen.add(key)
        landmarks.append(Landmark3D(kind, x, z, name or kind.title(), height))

    for element in osm_data.get("elements", []):
        tags = element.get("tags", {})
        kind = _classify(tags)
        if not kind:
            continue
        name = tags.get("name", "")

        if element["type"] == "node":
            x, z = lonlat_to_world_xz(projection, element["lon"], element["lat"])
            add(kind, x, z, name)
        elif element["type"] == "way" and kind == PARK:
            coords = [
                index.nodes[n]
                for n in element.get("nodes", [])
                if n in index.nodes
            ]
            if coords:
                lon = sum(c[0] for c in coords) / len(coords)
                lat = sum(c[1] for c in coords) / len(coords)
                x, z = lonlat_to_world_xz(projection, lon, lat)
                add(PARK, x, z, name, height=1.5)

    named_buildings = [
        e for e in osm_data.get("elements", [])
        if e.get("type") == "way"
        and "building" in e.get("tags", {})
        and e.get("tags", {}).get("name")
    ]
    for way in named_buildings[:40]:
        tags = way["tags"]
        coords = [index.nodes[n] for n in way.get("nodes", []) if n in index.nodes]
        if not coords:
            continue
        lon = sum(c[0] for c in coords) / len(coords)
        lat = sum(c[1] for c in coords) / len(coords)
        x, z = lonlat_to_world_xz(projection, lon, lat)
        h = float(tags.get("height", "15").split()[0]) if tags.get("height") else 15.0
        add(LANDMARK, x, z, tags["name"], min(h, 40))

    return landmarks


def load_landmarks_for_area(projection: GeoProjection) -> list[Landmark3D]:
    slug = projection.area_slug or "greenwich_village"
    path = DATA_DIR / f"{slug}_osm.json"
    if not path.exists():
        return []
    return load_landmarks(projection, json.loads(path.read_text()))

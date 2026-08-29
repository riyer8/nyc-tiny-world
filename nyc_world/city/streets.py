"""Real street network from OSM — roads, sidewalks, crossings, signals."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from nyc_world.map.buildings import lonlat_to_world_xz
from nyc_world.map.map_generator import OsmIndex
from nyc_world.paths import DATA_DIR
from nyc_world.city.pathfinding import build_adjacency, set_astar_positions
from nyc_world.core.projection import GeoProjection

ROAD_WIDTH_M: dict[str, float] = {
    "motorway": 12.0,
    "trunk": 10.0,
    "primary": 9.0,
    "secondary": 8.0,
    "tertiary": 7.0,
    "residential": 6.0,
    "living_street": 5.0,
    "unclassified": 6.0,
    "service": 4.0,
    "pedestrian": 5.0,
    "footway": 2.0,
    "path": 2.0,
    "steps": 2.0,
}

DRIVEABLE = frozenset(
    {
        "motorway",
        "trunk",
        "primary",
        "secondary",
        "tertiary",
        "residential",
        "living_street",
        "unclassified",
        "service",
    }
)

WALKABLE = DRIVEABLE | frozenset({"pedestrian", "footway", "path", "steps"})

SIDEWALK_WIDTH = 1.8
MARKING_SPACING = 4.0


@dataclass
class Quad:
    """Flat quad in world x/z, y is elevation."""

    x0: float
    z0: float
    x1: float
    z1: float
    x2: float
    z2: float
    x3: float
    z3: float
    y: float
    r: float
    g: float
    b: float


@dataclass
class TrafficLight3D:
    x: float
    z: float
    height: float = 4.5


@dataclass
class StreetScene:
    road_quads: list[Quad] = field(default_factory=list)
    sidewalk_quads: list[Quad] = field(default_factory=list)
    crosswalk_quads: list[Quad] = field(default_factory=list)
    marking_quads: list[Quad] = field(default_factory=list)
    traffic_lights: list[TrafficLight3D] = field(default_factory=list)


@dataclass
class StreetNetwork:
    positions: dict[int, tuple[float, float]]
    walk_graph: dict[int, list[tuple[int, float]]]
    drive_graph: dict[int, list[tuple[int, float]]]
    scene: StreetScene
    intersection_nodes: set[int]


def _perp(dx: float, dz: float, length: float) -> tuple[float, float]:
    if length < 1e-6:
        return 0.0, 0.0
    return -dz / length, dx / length


def _strip_quad(
    ax: float,
    az: float,
    bx: float,
    bz: float,
    half_w: float,
    y: float,
    color: tuple[float, float, float],
) -> Quad:
    dx, dz = bx - ax, bz - az
    length = math.hypot(dx, dz)
    px, pz = _perp(dx, dz, length)
    ox, oz = px * half_w, pz * half_w
    r, g, b = color
    return Quad(
        ax + ox, az + oz,
        bx + ox, bz + oz,
        bx - ox, bz - oz,
        ax - ox, az - oz,
        y, r, g, b,
    )


def _crosswalk_at(x: float, z: float, axis_x: float, axis_z: float) -> Quad:
    px, pz = _perp(axis_x, axis_z, 1.0)
    w, d = 3.0, 0.4
    return Quad(
        x + px * w - axis_x * d, z + pz * w - axis_z * d,
        x + px * w + axis_x * d, z + pz * w + axis_z * d,
        x - px * w + axis_x * d, z - pz * w + axis_z * d,
        x - px * w - axis_x * d, z - pz * w - axis_z * d,
        0.05, 0.92, 0.92, 0.88,
    )


def build_street_network(projection: GeoProjection, osm_data: dict) -> StreetNetwork:
    index = OsmIndex.from_osm(osm_data)
    scene = StreetScene()
    positions: dict[int, tuple[float, float]] = {}
    walk_edges: list[tuple[int, int, float]] = []
    drive_edges: list[tuple[int, int, float]] = []
    node_highways: dict[int, set[str]] = {}

    for way in index.ways.values():
        highway = way.get("tags", {}).get("highway")
        if not highway:
            continue
        node_ids = [n for n in way.get("nodes", []) if n in index.nodes]
        if len(node_ids) < 2:
            continue

        road_w = ROAD_WIDTH_M.get(highway, 5.0)
        road_color = (0.22, 0.22, 0.24)
        walk_color = (0.72, 0.70, 0.66)

        for i, nid in enumerate(node_ids):
            lon, lat = index.nodes[nid]
            positions[nid] = lonlat_to_world_xz(projection, lon, lat)
            node_highways.setdefault(nid, set()).add(highway)

        for i in range(len(node_ids) - 1):
            n0, n1 = node_ids[i], node_ids[i + 1]
            x0, z0 = positions[n0]
            x1, z1 = positions[n1]
            length = math.hypot(x1 - x0, z1 - z0)
            if length < 0.5:
                continue

            scene.road_quads.append(
                _strip_quad(x0, z0, x1, z1, road_w / 2, 0.04, road_color)
            )
            if highway in WALKABLE:
                scene.sidewalk_quads.append(
                    _strip_quad(x0, z0, x1, z1, road_w / 2 + SIDEWALK_WIDTH, 0.06, walk_color)
                )
                walk_edges.append((n0, n1, length))
            if highway in DRIVEABLE:
                drive_edges.append((n0, n1, length))

            if highway in DRIVEABLE and road_w >= 6:
                dx, dz = (x1 - x0) / length, (z1 - z0) / length
                dist = MARKING_SPACING
                while dist < length - MARKING_SPACING:
                    mx, mz = x0 + dx * dist, z0 + dz * dist
                    scene.marking_quads.append(
                        _strip_quad(
                            mx - dx * 1.2, mz - dz * 1.2,
                            mx + dx * 1.2, mz + dz * 1.2,
                            0.15, 0.05, (0.9, 0.85, 0.5),
                        )
                    )
                    dist += MARKING_SPACING * 2

    intersection_nodes: set[int] = set()
    for nid, types in node_highways.items():
        if len(types) >= 2 or any(t in DRIVEABLE for t in types):
            intersection_nodes.add(nid)

    for nid in intersection_nodes:
        x, z = positions[nid]
        scene.crosswalk_quads.append(_crosswalk_at(x, z, 1.0, 0.0))
        scene.crosswalk_quads.append(_crosswalk_at(x, z, 0.0, 1.0))
        if any(t in DRIVEABLE for t in node_highways.get(nid, ())):
            scene.traffic_lights.append(TrafficLight3D(x, z))

    for element in osm_data.get("elements", []):
        if element.get("type") != "node":
            continue
        tags = element.get("tags", {})
        if tags.get("highway") == "traffic_signals":
            x, z = lonlat_to_world_xz(projection, element["lon"], element["lat"])
            scene.traffic_lights.append(TrafficLight3D(x, z))

    walk_graph = build_adjacency(walk_edges)
    drive_graph = build_adjacency(drive_edges)
    set_astar_positions(positions)

    return StreetNetwork(
        positions=positions,
        walk_graph=walk_graph,
        drive_graph=drive_graph,
        scene=scene,
        intersection_nodes=intersection_nodes,
    )


def load_street_network(projection: GeoProjection) -> StreetNetwork | None:
    slug = projection.area_slug or "greenwich_village"
    path = DATA_DIR / f"{slug}_osm.json"
    if not path.exists():
        return None
    osm_data = json.loads(path.read_text())
    return build_street_network(projection, osm_data)

"""Convert OpenStreetMap data into a game tile map."""

from __future__ import annotations

import random
from dataclasses import dataclass

from shapely.geometry import LineString, Polygon

from nyc_world.core.areas import Area
from nyc_world.core.projection import GeoProjection
from nyc_world.core.sprites import (
    BUILDING,
    PARK,
    PLAYER_SPAWN,
    POI,
    ROAD,
    SIDEWALK,
    TREE,
)

# Major roads get more tiles wide.
HIGHWAY_WIDTH = {
    "motorway": 4,
    "trunk": 3,
    "primary": 3,
    "secondary": 2,
    "tertiary": 2,
    "residential": 1,
    "living_street": 1,
    "service": 1,
    "footway": 1,
    "path": 1,
    "pedestrian": 2,
    "unclassified": 1,
}

PARK_TAGS = {
    ("leisure", "park"),
    ("leisure", "garden"),
    ("landuse", "grass"),
    ("landuse", "recreation_ground"),
    ("landuse", "forest"),
    ("landuse", "meadow"),
}


@dataclass
class OsmIndex:
    nodes: dict[int, tuple[float, float]]
    ways: dict[int, dict]
    relations: dict[int, dict]

    @classmethod
    def from_osm(cls, data: dict) -> OsmIndex:
        nodes: dict[int, tuple[float, float]] = {}
        ways: dict[int, dict] = {}
        relations: dict[int, dict] = {}

        for element in data.get("elements", []):
            kind = element["type"]
            if kind == "node":
                nodes[element["id"]] = (element["lon"], element["lat"])
            elif kind == "way":
                ways[element["id"]] = element
            elif kind == "relation":
                relations[element["id"]] = element

        return cls(nodes=nodes, ways=ways, relations=relations)


@dataclass
class GeneratedMap:
    text: str
    projection: GeoProjection


class MapGenerator:
    def __init__(
        self,
        area: Area,
        osm_data: dict,
        projection: GeoProjection,
        *,
        tree_density: float = 0.15,
        seed: int = 42,
    ) -> None:
        self.area = area
        self.projection = projection
        self.cols = projection.cols
        self.rows = projection.rows
        self.tree_density = tree_density
        self.rng = random.Random(seed)
        self.index = OsmIndex.from_osm(osm_data)
        self.grid: list[list[str]] = [
            [SIDEWALK for _ in range(self.cols)] for _ in range(self.rows)
        ]

    def _way_coords(self, way: dict) -> list[tuple[float, float]]:
        return [
            self.index.nodes[node_id]
            for node_id in way.get("nodes", [])
            if node_id in self.index.nodes
        ]

    def _relation_polygons(self, relation: dict) -> list[Polygon]:
        outers: list[LineString] = []
        inners: list[LineString] = []

        for member in relation.get("members", []):
            if member.get("type") != "way":
                continue
            way = self.index.ways.get(member["ref"])
            if not way:
                continue
            coords = self._way_coords(way)
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

    def _tile_bbox_polygon(self, col: int, row: int) -> Polygon:
        corners = self.projection.tile_bbox_polygon_lonlat(col, row)
        return Polygon(corners)

    def _fill_polygon(self, polygon: Polygon, tile: str) -> None:
        minx, miny, maxx, maxy = polygon.bounds
        min_col, north_row = self.projection.to_tile(maxy, minx)
        max_col, south_row = self.projection.to_tile(miny, maxx)
        col_start, col_end = sorted((min_col, max_col))
        row_start, row_end = sorted((north_row, south_row))

        for row in range(row_start, row_end + 1):
            for col in range(col_start, col_end + 1):
                if polygon.intersects(self._tile_bbox_polygon(col, row)):
                    self.grid[row][col] = tile

    def _draw_roads(self) -> None:
        for way in self.index.ways.values():
            tags = way.get("tags", {})
            highway = tags.get("highway")
            if not highway:
                continue
            coords = self._way_coords(way)
            if len(coords) < 2:
                continue

            width_tiles = HIGHWAY_WIDTH.get(highway, 1)
            line = LineString(coords)
            buffer_m = max(width_tiles * self.projection.meters_per_tile() * 0.45, 4.0)
            buffered = line.buffer(self.projection.meters_to_degrees(buffer_m))
            self._fill_polygon(buffered, ROAD)

    def _draw_buildings(self) -> None:
        for way in self.index.ways.values():
            if "building" not in way.get("tags", {}):
                continue
            coords = self._way_coords(way)
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
                if poly.is_valid:
                    self._fill_polygon(poly, BUILDING)
            except Exception:
                continue

        for relation in self.index.relations.values():
            if "building" not in relation.get("tags", {}):
                continue
            for poly in self._relation_polygons(relation):
                self._fill_polygon(poly, BUILDING)

    def _is_park_way(self, tags: dict) -> bool:
        return any(tags.get(k) == v for k, v in PARK_TAGS)

    def _draw_parks(self) -> None:
        for way in self.index.ways.values():
            tags = way.get("tags", {})
            if not self._is_park_way(tags):
                continue
            coords = self._way_coords(way)
            if len(coords) < 3:
                continue
            try:
                poly = Polygon(coords)
                if poly.is_valid:
                    self._fill_polygon(poly, PARK)
            except Exception:
                continue

        for relation in self.index.relations.values():
            tags = relation.get("tags", {})
            if tags.get("leisure") != "park" and not self._is_park_way(tags):
                continue
            for poly in self._relation_polygons(relation):
                self._fill_polygon(poly, PARK)

    def _draw_pois(self) -> None:
        for element in self._elements:
            if element.get("type") != "node":
                continue
            tags = element.get("tags", {})
            if not (tags.get("amenity") or tags.get("shop") or tags.get("tourism")):
                continue
            lon, lat = element["lon"], element["lat"]
            col, row = self.projection.to_tile(lat, lon)
            if self.grid[row][col] in (SIDEWALK, ROAD, PARK):
                self.grid[row][col] = POI

    def _scatter_trees(self) -> None:
        for row in range(self.rows):
            for col in range(self.cols):
                if self.grid[row][col] == PARK and self.rng.random() < self.tree_density:
                    self.grid[row][col] = TREE

    def _place_player(self) -> tuple[int, int]:
        col, row = self.projection.to_tile(
            self.area.spawn_lat, self.area.spawn_lon
        )
        if self.grid[row][col] in SOLID_FOR_SPAWN:
            for radius in range(1, max(self.cols, self.rows)):
                for dc in range(-radius, radius + 1):
                    for dr in range(-radius, radius + 1):
                        c, r = col + dc, row + dr
                        if 0 <= c < self.cols and 0 <= r < self.rows:
                            if self.grid[r][c] not in SOLID_FOR_SPAWN:
                                return c, r
        return col, row

    def generate(self, elements: list[dict]) -> GeneratedMap:
        self._elements = elements
        self._draw_parks()
        self._draw_roads()
        self._draw_buildings()
        self._draw_pois()
        self._scatter_trees()

        spawn_col, spawn_row = self._place_player()
        self.grid[spawn_row][spawn_col] = PLAYER_SPAWN

        text = "\n".join("".join(row) for row in self.grid)
        return GeneratedMap(text=text, projection=self.projection)


SOLID_FOR_SPAWN = frozenset({BUILDING, TREE})


def generate_map(
    area: Area,
    osm_data: dict,
    *,
    cols: int = 80,
    rows: int = 80,
    tile_size: int = 16,
) -> GeneratedMap:
    projection = GeoProjection.from_area(
        area, cols=cols, rows=rows, tile_size=tile_size
    )
    generator = MapGenerator(area, osm_data, projection)
    return generator.generate(osm_data.get("elements", []))

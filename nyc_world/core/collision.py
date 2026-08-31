"""Circle-vs-polygon collision for OSM building footprints."""

from __future__ import annotations

import math

from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points
from shapely.strtree import STRtree

from nyc_world.map.buildings import Building3D

# Leave a walkable strip at the lot line (sidewalk / door approach).
BUILDING_INSET_M = 1.1


def _footprint_polygons(buildings: list[Building3D], inset_m: float) -> list[Polygon]:
    polys: list[Polygon] = []
    for building in buildings:
        if len(building.footprint) < 3:
            continue
        ring = [(x, z) for x, z in building.footprint]
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.is_empty:
            continue
        shrunk = poly.buffer(-inset_m)
        if shrunk.is_empty:
            continue
        if shrunk.geom_type == "Polygon":
            polys.append(shrunk)
        elif shrunk.geom_type == "MultiPolygon":
            polys.extend(shrunk.geoms)
    return polys


class BuildingCollision:
    """Spatial index for player-vs-building footprint tests."""

    def __init__(self, buildings: list[Building3D], *, inset_m: float = BUILDING_INSET_M) -> None:
        self._polys = _footprint_polygons(buildings, inset_m)
        self._tree = STRtree(self._polys) if self._polys else None

    def is_blocked(self, x: float, z: float, radius: float) -> bool:
        if not self._tree:
            return False
        body = Point(x, z).buffer(radius)
        for idx in self._tree.query(body):
            if self._polys[int(idx)].intersects(body):
                return True
        return False

    def push_out(self, x: float, z: float, radius: float, *, ox: float, oz: float) -> tuple[float, float]:
        """Nudge the player circle out of building footprints."""
        if not self._tree or not self.is_blocked(x, z, radius):
            return x, z

        pt = Point(x, z)
        for _ in range(8):
            body = pt.buffer(radius)
            moved = False
            for idx in self._tree.query(body):
                poly = self._polys[int(idx)]
                if not body.intersects(poly):
                    continue
                boundary_pt = nearest_points(pt, poly.boundary)[1]
                dx = pt.x - boundary_pt.x
                dz = pt.y - boundary_pt.y
                dist = math.hypot(dx, dz)
                if dist < 1e-6:
                    dx, dz = pt.x - ox, pt.y - oz
                    dist = math.hypot(dx, dz)
                if dist < 1e-6:
                    return ox, oz
                clearance = radius + 0.08
                if poly.contains(pt):
                    push = poly.boundary.distance(pt) + clearance
                else:
                    push = clearance - poly.boundary.distance(pt)
                if push > 0:
                    pt = Point(pt.x + dx / dist * push, pt.y + dz / dist * push)
                    moved = True
                    break
            if not moved or not self.is_blocked(pt.x, pt.y, radius):
                break
        return pt.x, pt.y


class BuildingFootprintIndex:
    """Full-size building footprints for camera placement (visual mesh bounds)."""

    def __init__(self, buildings: list[Building3D]) -> None:
        self._polys = _footprint_polygons(buildings, inset_m=0.0)
        self._tree = STRtree(self._polys) if self._polys else None

    def clamp_camera(self, ex: float, ez: float, px: float, pz: float, *, margin: float = 0.45) -> tuple[float, float]:
        """Keep the camera eye outside building volumes so walls stay visible."""
        if not self._tree:
            return ex, ez
        for _ in range(10):
            pt = Point(ex, ez)
            moved = False
            for idx in self._tree.query(pt):
                poly = self._polys[int(idx)]
                if not poly.contains(pt):
                    continue
                boundary_pt = nearest_points(pt, poly.boundary)[1]
                dx = ex - boundary_pt.x
                dz = ez - boundary_pt.y
                dist = math.hypot(dx, dz)
                if dist < 1e-6:
                    dx, dz = ex - px, ez - pz
                    dist = math.hypot(dx, dz)
                if dist < 1e-6:
                    return px, pz + 2.0
                push = poly.boundary.distance(pt) + margin
                ex = boundary_pt.x + dx / dist * push
                ez = boundary_pt.y + dz / dist * push
                moved = True
                break
            if not moved:
                break
        return ex, ez

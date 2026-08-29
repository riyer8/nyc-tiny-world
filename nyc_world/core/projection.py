"""Geographic projection: GPS coordinates ↔ game pixel coordinates.

Uses a local east-north-up (ENU) tangent plane so compass directions match
the real world:

  +x  →  east  (longitude increases)
  +y  →  south (latitude decreases, screen coordinates)
  -y  →  north
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from nyc_world.core.areas import Area

METERS_PER_DEGREE_LAT = 111_320.0


@dataclass(frozen=True)
class GeoProjection:
    """Map a geographic bounding box onto a pixel rectangle."""

    south: float
    west: float
    north: float
    east: float
    width_px: float
    height_px: float
    tile_size: int
    cols: int
    rows: int
    area_slug: str = ""
    area_name: str = ""

    @classmethod
    def from_area(
        cls,
        area: Area,
        *,
        cols: int,
        rows: int,
        tile_size: int,
    ) -> GeoProjection:
        return cls(
            south=area.south,
            west=area.west,
            north=area.north,
            east=area.east,
            width_px=cols * tile_size,
            height_px=rows * tile_size,
            tile_size=tile_size,
            cols=cols,
            rows=rows,
            area_slug=area.slug,
            area_name=area.name,
        )

    @classmethod
    def from_file(cls, path: str | Path) -> GeoProjection:
        data = json.loads(Path(path).read_text())
        return cls(**{k: data[k] for k in cls.__dataclass_fields__ if k in data})

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n")

    @property
    def lat_mid(self) -> float:
        return (self.south + self.north) / 2

    @property
    def meters_per_degree_lon(self) -> float:
        return METERS_PER_DEGREE_LAT * math.cos(math.radians(self.lat_mid))

    @property
    def east_span_m(self) -> float:
        return (self.east - self.west) * self.meters_per_degree_lon

    @property
    def north_span_m(self) -> float:
        return (self.north - self.south) * METERS_PER_DEGREE_LAT

    @property
    def meters_per_pixel_x(self) -> float:
        return self.east_span_m / self.width_px

    @property
    def meters_per_pixel_y(self) -> float:
        return self.north_span_m / self.height_px

    def lon_to_meters_east(self, lon: float) -> float:
        return (lon - self.west) * self.meters_per_degree_lon

    def lat_to_meters_north(self, lat: float) -> float:
        return (lat - self.south) * METERS_PER_DEGREE_LAT

    def meters_east_to_lon(self, east_m: float) -> float:
        return self.west + east_m / self.meters_per_degree_lon

    def meters_north_to_lat(self, north_m: float) -> float:
        return self.south + north_m / METERS_PER_DEGREE_LAT

    def to_game(self, lat: float, lon: float) -> tuple[float, float]:
        """GPS → pixel coordinates. Example: (40.73061, -73.9973) → (481.2, 327.8)."""
        east_m = self.lon_to_meters_east(lon)
        north_m = self.lat_to_meters_north(lat)
        x = east_m / self.east_span_m * self.width_px
        y = (self.north_span_m - north_m) / self.north_span_m * self.height_px
        return x, y

    def to_gps(self, x: float, y: float) -> tuple[float, float]:
        """Pixel coordinates → GPS. Returns (latitude, longitude)."""
        east_m = x / self.width_px * self.east_span_m
        north_m = self.north_span_m - (y / self.height_px * self.north_span_m)
        lat = self.meters_north_to_lat(north_m)
        lon = self.meters_east_to_lon(east_m)
        return lat, lon

    def to_tile(self, lat: float, lon: float) -> tuple[int, int]:
        x, y = self.to_game(lat, lon)
        col = int(x / self.tile_size)
        row = int(y / self.tile_size)
        col = max(0, min(self.cols - 1, col))
        row = max(0, min(self.rows - 1, row))
        return col, row

    def tile_center_game(self, col: int, row: int) -> tuple[float, float]:
        x = (col + 0.5) * self.tile_size
        y = (row + 0.5) * self.tile_size
        return x, y

    def tile_center_gps(self, col: int, row: int) -> tuple[float, float]:
        x, y = self.tile_center_game(col, row)
        return self.to_gps(x, y)

    def tile_bbox_polygon_lonlat(self, col: int, row: int) -> list[tuple[float, float]]:
        """Tile corners as (lon, lat) for shapely — west→east, south→north."""
        x0 = col * self.tile_size
        x1 = (col + 1) * self.tile_size
        y0 = row * self.tile_size
        y1 = (row + 1) * self.tile_size
        sw = self.to_gps(x0, y1)
        se = self.to_gps(x1, y1)
        ne = self.to_gps(x1, y0)
        nw = self.to_gps(x0, y0)
        return [
            (sw[1], sw[0]),
            (se[1], se[0]),
            (ne[1], ne[0]),
            (nw[1], nw[0]),
        ]

    def meters_to_degrees(self, meters: float) -> float:
        return meters / METERS_PER_DEGREE_LAT

    def meters_per_tile(self) -> float:
        return (self.meters_per_pixel_x + self.meters_per_pixel_y) / 2 * self.tile_size

"""Geographic regions for hierarchical mini-map context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeoRegion:
    name: str
    south: float
    west: float
    north: float
    east: float

    def contains(self, lat: float, lon: float) -> bool:
        return self.south <= lat <= self.north and self.west <= lon <= self.east

    def normalize(self, lat: float, lon: float) -> tuple[float, float]:
        """Map lat/lon to 0..1 inside this region (x=east, y=north-up)."""
        x = (lon - self.west) / (self.east - self.west)
        y = (lat - self.south) / (self.north - self.south)
        return max(0.0, min(1.0, x)), max(0.0, min(1.0, y))


# Rough bounding boxes for orientation — not exact coastlines.
NYC = GeoRegion("NYC", south=40.49, west=-74.26, north=40.92, east=-73.70)
MANHATTAN = GeoRegion("Manhattan", south=40.700, west=-74.020, north=40.882, east=-73.907)
BROOKLYN = GeoRegion("Brooklyn", south=40.570, west=-74.042, north=40.739, east=-73.833)

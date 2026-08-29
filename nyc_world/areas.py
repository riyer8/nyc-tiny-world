"""Tiny real-world areas to import from OpenStreetMap."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Area:
    name: str
    slug: str
    south: float
    west: float
    north: float
    east: float
    spawn_lat: float
    spawn_lon: float
    description: str

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        return self.south, self.west, self.north, self.east


# ~1 km × 1 km around Washington Square Park — heart of Greenwich Village.
GREENWICH_VILLAGE = Area(
    name="Greenwich Village",
    slug="greenwich_village",
    south=40.7263,
    west=-74.0033,
    north=40.7353,
    east=-73.9913,
    spawn_lat=40.7308,
    spawn_lon=-73.9973,
    description="~1 km² around Washington Square Park",
)

AREAS: dict[str, Area] = {
    GREENWICH_VILLAGE.slug: GREENWICH_VILLAGE,
}

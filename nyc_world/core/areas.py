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


# ~500 m × 500 m around Washington Square Park — focused playable area.
WASHINGTON_SQUARE = Area(
    name="Washington Square",
    slug="washington_square",
    south=40.7285,
    west=-74.0003,
    north=40.7331,
    east=-73.9943,
    spawn_lat=40.7308,
    spawn_lon=-73.9973,
    description="~500 m around Washington Square Park",
)

# ~1 km × 1 km around Washington Square Park — broader Greenwich Village.
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
    WASHINGTON_SQUARE.slug: WASHINGTON_SQUARE,
    GREENWICH_VILLAGE.slug: GREENWICH_VILLAGE,
}

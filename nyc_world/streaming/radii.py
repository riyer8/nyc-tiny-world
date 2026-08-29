"""Level-of-detail radii for the streaming world."""

from __future__ import annotations

from dataclasses import dataclass

METERS_PER_MILE = 1609.344


@dataclass(frozen=True)
class StreamRadii:
    """Concentric radii around the player."""

    data_m: float = 5.0 * METERS_PER_MILE  # ~8 km — fetch/cache OSM tiles
    render_3d_m: float = 1.0 * METERS_PER_MILE  # ~1.6 km — detailed 3D geometry
    simulation_m: float = 300.0  # NPCs, vehicles, clock-driven actors
    interaction_m: float = 100.0  # interactables, interiors, quest objects

    @property
    def data_miles(self) -> float:
        return self.data_m / METERS_PER_MILE

    @property
    def render_3d_miles(self) -> float:
        return self.render_3d_m / METERS_PER_MILE


DEFAULT_RADII = StreamRadii()

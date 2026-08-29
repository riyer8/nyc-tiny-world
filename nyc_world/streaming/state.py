"""Streaming state snapshot for HUD and mini-map."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.streaming.radii import DEFAULT_RADII


@dataclass
class StreamingState:
    player_lat: float = 0.0
    player_lon: float = 0.0
    player_tile: str = ""
    loaded_tile_ids: set[str] = field(default_factory=set)
    data_radius_m: float = DEFAULT_RADII.data_m
    render_radius_m: float = DEFAULT_RADII.render_3d_m
    simulation_radius_m: float = DEFAULT_RADII.simulation_m
    far_building_markers: list[tuple[float, float]] = field(default_factory=list)
    buildings_in_render: int = 0
    buildings_in_data: int = 0

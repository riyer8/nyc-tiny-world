"""Graphics quality presets — trade visual range for frame rate."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GraphicsProfile:
    name: str
    building_draw_radius_m: float
    draw_far_skyline: bool
    npc_count: int
    vehicle_count: int
    minimap_interval_s: float


FAST = GraphicsProfile(
    name="fast",
    building_draw_radius_m=200.0,
    draw_far_skyline=False,
    npc_count=20,
    vehicle_count=12,
    minimap_interval_s=0.6,
)

NORMAL = GraphicsProfile(
    name="normal",
    building_draw_radius_m=450.0,
    draw_far_skyline=True,
    npc_count=48,
    vehicle_count=32,
    minimap_interval_s=0.25,
)

PROFILES = {"fast": FAST, "normal": NORMAL}


def get_profile(name: str) -> GraphicsProfile:
    return PROFILES.get(name, FAST)

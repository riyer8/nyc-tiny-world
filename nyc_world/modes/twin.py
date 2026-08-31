"""Digital twin mode — elevated city view with sim controls."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nyc_world.city.npcs import NPC
    from nyc_world.city.vehicles import Vehicle
    from nyc_world.simulation.agent import AgentController
    from nyc_world.simulation.npc_mind import NPCMindRegistry


TIME_SCALES = (1.0, 10.0, 30.0)
HEATMAP_MODES = (None, "density", "traffic", "mood")


@dataclass
class TwinMode:
    """Overhead city simulation view with pause, time scale, and entity inspect."""

    active: bool = False
    paused: bool = False
    time_scale: float = 1.0
    heatmap: str | None = None
    camera_height: float = 80.0
    camera_distance: float = 55.0
    selected_id: str | None = None
    selected_kind: str | None = None
    _saved_player_pos: tuple[float, float] | None = field(default=None, repr=False)

    def toggle(self) -> bool:
        self.active = not self.active
        if not self.active:
            self.selected_id = None
            self.selected_kind = None
            self.paused = False
        return self.active

    def toggle_pause(self) -> bool:
        self.paused = not self.paused
        return self.paused

    def set_time_scale(self, scale: float) -> None:
        if scale in TIME_SCALES:
            self.time_scale = scale

    def cycle_heatmap(self) -> str | None:
        if self.heatmap is None:
            self.heatmap = "density"
        elif self.heatmap == "density":
            self.heatmap = "traffic"
        elif self.heatmap == "traffic":
            self.heatmap = "mood"
        else:
            self.heatmap = None
        return self.heatmap

    def adjust_zoom(self, delta: int) -> None:
        self.camera_height = max(25.0, min(200.0, self.camera_height - delta * 8.0))
        self.camera_distance = max(20.0, min(150.0, self.camera_distance - delta * 5.0))

    def effective_speed_multiplier(self, base: float = 1.0) -> float:
        if not self.active or self.paused:
            return 0.0
        return base * self.time_scale

    def hud_lines(self, *, npc_count: int, vehicle_count: int, tick: int, weather: str, time_str: str) -> list[str]:
        pause_icon = "⏸" if self.paused else "▶"
        scale_label = f"{int(self.time_scale)}×"
        lines = [
            f"🌎 CITY SIMULATION  [{pause_icon}] [{scale_label}]",
            "─" * 36,
            f"NPCs: {npc_count} active   Vehicles: {vehicle_count}   Tick: {tick}",
            f"Weather: {weather} · {time_str}",
        ]
        if self.heatmap:
            lines.append(f"Heatmap: {self.heatmap}")
        lines.extend(["", "T: exit twin · Space: pause · 1/2/3: speed · H: heatmap"])
        return lines

    def select_nearest(
        self,
        npcs: list[NPC],
        vehicles: list[Vehicle],
        cx: float,
        cz: float,
        *,
        radius: float = 60.0,
    ) -> bool:
        radius_sq = radius * radius
        best_id: str | None = None
        best_kind: str | None = None
        best_d = radius_sq

        for npc in npcs:
            dx, dz = npc.x - cx, npc.z - cz
            d = dx * dx + dz * dz
            if d < best_d:
                best_d = d
                best_id = npc.name
                best_kind = "npc"

        for i, vehicle in enumerate(vehicles):
            dx, dz = vehicle.x - cx, vehicle.z - cz
            d = dx * dx + dz * dz
            if d < best_d:
                best_d = d
                best_id = f"vehicle_{i}"
                best_kind = "vehicle"

        if best_id:
            self.selected_id = best_id
            self.selected_kind = best_kind
            return True
        return False

    def inspector_lines(
        self,
        npc_id: str,
        *,
        minds: NPCMindRegistry,
        agents: AgentController | None,
    ) -> list[str]:
        if not npc_id:
            return []
        brain = agents.get(npc_id) if agents else None
        mind = minds.get(npc_id)
        lines = [npc_id.replace("_", " ").title(), "─" * 20]
        if brain:
            lines.append(brain.personality.summary())
            lines.append(brain.needs.bars_summary())
            lines.append(f"Goal: {brain.goal_text or brain.plan_summary}")
            lines.append(f"Action: {brain.current_action}")
        elif mind:
            lines.append(f"Goal: {mind.current_goal_text()}")
            lines.append(f"Mood: {mind.mood:.2f}")
        rel = minds.relationships.get(npc_id)
        lines.append(f"Trust: {rel.trust:.0f}  Friendship: {rel.friendship:.0f}")
        return lines

    def heatmap_color(self, npc: NPC, *, minds: NPCMindRegistry, nearby_count: int) -> tuple[float, float, float]:
        if self.heatmap == "mood":
            mind = minds.get(npc.name)
            mood = mind.mood if mind else 0.5
            return (1.0 - mood, mood, 0.3)
        if self.heatmap == "density":
            t = min(1.0, nearby_count / 8.0)
            return (0.3 + t * 0.5, 0.2, 1.0 - t * 0.5)
        return npc.color

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "paused": self.paused,
            "time_scale": self.time_scale,
            "heatmap": self.heatmap,
            "camera_height": self.camera_height,
            "camera_distance": self.camera_distance,
            "selected_id": self.selected_id,
            "selected_kind": self.selected_kind,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TwinMode:
        return cls(
            active=data.get("active", False),
            paused=data.get("paused", False),
            time_scale=data.get("time_scale", 1.0),
            heatmap=data.get("heatmap"),
            camera_height=data.get("camera_height", 80.0),
            camera_distance=data.get("camera_distance", 55.0),
            selected_id=data.get("selected_id"),
            selected_kind=data.get("selected_kind"),
        )

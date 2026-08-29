"""Orchestrates the living city simulation."""

from __future__ import annotations

from nyc_world.landmarks import load_landmarks_for_area
from nyc_world.npcs import spawn_npcs
from nyc_world.projection import GeoProjection
from nyc_world.streets import StreetNetwork, load_street_network
from nyc_world.vehicles import spawn_vehicles
from nyc_world.world_clock import WorldClock


class CitySimulation:
    """Streets, landmarks, NPCs, vehicles, and time/weather."""

    def __init__(
        self,
        projection: GeoProjection,
        spawn_x: float,
        spawn_z: float,
        *,
        npc_count: int = 24,
        vehicle_count: int = 18,
    ) -> None:
        self.projection = projection
        self.clock = WorldClock(hour=8, minute=0)
        self.streets: StreetNetwork | None = load_street_network(projection)
        self.landmarks = load_landmarks_for_area(projection)

        if self.streets:
            self.npcs = spawn_npcs(
                self.streets, self.landmarks, spawn_x, spawn_z, count=npc_count
            )
            self.vehicles = spawn_vehicles(self.streets, count=vehicle_count)
        else:
            self.npcs = []
            self.vehicles = []

    def update(self, dt: float) -> None:
        self.clock.advance(dt)
        if not self.streets:
            return
        game_minutes = self.clock.hour * 60 + self.clock.minute + self.clock.minute / 60.0
        for npc in self.npcs:
            if self.clock.is_raining and npc.personality == "commuter":
                npc.speed = max(1.0, npc.speed)
            npc.update(dt, self.clock, self.streets, game_minutes)
        for vehicle in self.vehicles:
            vehicle.update(dt, self.streets)

    @property
    def street_scene(self):
        return self.streets.scene if self.streets else None

    def summary(self) -> str:
        parts = [
            f"{len(self.landmarks)} landmarks",
            f"{len(self.npcs)} NPCs",
            f"{len(self.vehicles)} vehicles",
        ]
        if self.streets:
            parts.insert(0, f"{len(self.streets.scene.road_quads)} road segments")
        return ", ".join(parts)

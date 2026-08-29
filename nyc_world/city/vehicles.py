"""Vehicles that follow the road graph."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from nyc_world.city.pathfinding import astar, path_to_world
from nyc_world.city.streets import StreetNetwork

TAXI = "taxi"
CAR = "car"
BUS = "bus"
BIKE = "bike"

VEHICLE_SPEED = {TAXI: 8.0, CAR: 6.0, BUS: 4.5, BIKE: 3.5}
VEHICLE_COLOR = {
    TAXI: (0.95, 0.82, 0.1),
    CAR: (0.75, 0.2, 0.2),
    BUS: (0.15, 0.35, 0.75),
    BIKE: (0.2, 0.7, 0.3),
}


@dataclass
class Vehicle:
    kind: str
    x: float
    z: float
    heading: float = 0.0
    speed: float = 6.0
    path: list[tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    wait: float = 0.0
    color: tuple[float, float, float] = (0.8, 0.2, 0.2)

    def update(self, dt: float, streets: StreetNetwork) -> None:
        if self.wait > 0:
            self.wait -= dt
            return
        if not self.path or self.path_index >= len(self.path):
            self._new_route(streets)
            return

        tx, tz = self.path[self.path_index]
        dx, dz = tx - self.x, tz - self.z
        dist = math.hypot(dx, dz)
        step = self.speed * dt
        if dist <= step:
            self.x, self.z = tx, tz
            self.path_index += 1
            if self.path_index >= len(self.path):
                self.wait = random.uniform(2, 8)
        else:
            self.x += dx / dist * step
            self.z += dz / dist * step
            self.heading = math.atan2(dx, dz)

    def _new_route(self, streets: StreetNetwork) -> None:
        nodes = [n for n in streets.drive_graph if streets.drive_graph[n]]
        if len(nodes) < 2:
            return
        start, goal = random.sample(nodes, 2)
        node_path = astar(streets.drive_graph, start, goal)
        if node_path:
            self.path = path_to_world(node_path, streets.positions)
            self.path_index = 0


def spawn_vehicles(
    streets: StreetNetwork,
    count: int = 18,
    seed: int = 99,
) -> list[Vehicle]:
    rng = random.Random(seed)
    kinds = [TAXI, CAR, CAR, CAR, BUS, BIKE, BIKE]
    vehicles: list[Vehicle] = []
    nodes = list(streets.positions.items())
    if not nodes:
        return []

    for i in range(count):
        kind = kinds[i % len(kinds)]
        _, (x, z) = rng.choice(nodes)
        vehicles.append(
            Vehicle(
                kind=kind,
                x=x,
                z=z,
                speed=VEHICLE_SPEED[kind] * rng.uniform(0.85, 1.1),
                color=VEHICLE_COLOR[kind],
            )
        )
    return vehicles

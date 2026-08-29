"""NPCs with schedules, personalities, and street navigation."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from nyc_world.city.landmarks import CAFE, LANDMARK, PARK, STORE, SUBWAY, Landmark3D
from nyc_world.city.pathfinding import astar, path_to_world
from nyc_world.city.streets import StreetNetwork
from nyc_world.city.world_clock import WorldClock


@dataclass
class ScheduleStop:
    hour: int
    minute: int
    dest_x: float
    dest_z: float
    label: str


@dataclass
class NPC:
    name: str
    personality: str
    x: float
    z: float
    speed: float
    schedule: list[ScheduleStop]
    schedule_index: int = 0
    path: list[tuple[float, float]] = field(default_factory=list)
    path_index: int = 0
    wait_until: float = 0.0
    has_umbrella: bool = False
    color: tuple[float, float, float] = (0.8, 0.3, 0.3)

    def current_stop(self) -> ScheduleStop:
        return self.schedule[self.schedule_index % len(self.schedule)]

    def update(
        self,
        dt: float,
        clock: WorldClock,
        streets: StreetNetwork,
        game_minutes: float,
    ) -> None:
        if clock.is_raining:
            self.has_umbrella = True
        elif not clock.is_raining and clock.weather.value == "clear":
            self.has_umbrella = False

        if game_minutes < self.wait_until:
            return

        if not self.path or self.path_index >= len(self.path):
            self._advance_schedule(clock, streets, game_minutes)
            return

        target_x, target_z = self.path[self.path_index]
        dx, dz = target_x - self.x, target_z - self.z
        dist = math.hypot(dx, dz)
        step = self.speed * dt
        if clock.is_raining:
            step *= 0.85

        if dist <= step:
            self.x, self.z = target_x, target_z
            self.path_index += 1
            if self.path_index >= len(self.path):
                stop = self.current_stop()
                self.wait_until = game_minutes + 15 + random.random() * 20
        else:
            self.x += dx / dist * step
            self.z += dz / dist * step

    def _advance_schedule(
        self,
        clock: WorldClock,
        streets: StreetNetwork,
        game_minutes: float,
    ) -> None:
        stop = self.current_stop()
        stop_minutes = stop.hour * 60 + stop.minute
        now_minutes = clock.hour * 60 + clock.minute

        if now_minutes < stop_minutes and now_minutes + 12 * 60 > stop_minutes:
            return

        self._route_to(streets, stop.dest_x, stop.dest_z)
        self.schedule_index = (self.schedule_index + 1) % len(self.schedule)

    def _route_to(self, streets: StreetNetwork, tx: float, tz: float) -> None:
        start = _nearest_node(streets, self.x, self.z)
        goal = _nearest_node(streets, tx, tz)
        if start is None or goal is None:
            self.path = [(tx, tz)]
            self.path_index = 0
            return
        node_path = astar(streets.walk_graph, start, goal)
        if not node_path:
            self.path = [(tx, tz)]
        else:
            self.path = path_to_world(node_path, streets.positions)
            if self.path:
                self.path.append((tx, tz))
        self.path_index = 0


def _nearest_node(streets: StreetNetwork, x: float, z: float) -> int | None:
    best: int | None = None
    best_d = float("inf")
    for nid, (nx, nz) in streets.positions.items():
        if nid not in streets.walk_graph:
            continue
        d = (nx - x) ** 2 + (nz - z) ** 2
        if d < best_d:
            best_d = d
            best = nid
    return best


def _pick_by_kind(landmarks: list[Landmark3D], kind: str) -> list[Landmark3D]:
    return [lm for lm in landmarks if lm.kind == kind]


def _schedule_commuter(
    home: tuple[float, float],
    work: tuple[float, float],
    subway: tuple[float, float],
    lunch: tuple[float, float],
) -> list[ScheduleStop]:
    hx, hz = home
    wx, wz = work
    sx, sz = subway
    lx, lz = lunch
    return [
        ScheduleStop(8, 0, hx, hz, "home"),
        ScheduleStop(8, 30, sx, sz, "subway"),
        ScheduleStop(9, 0, wx, wz, "work"),
        ScheduleStop(12, 0, lx, lz, "lunch"),
        ScheduleStop(13, 0, wx, wz, "work"),
        ScheduleStop(17, 30, sx, sz, "subway"),
        ScheduleStop(18, 0, hx, hz, "home"),
    ]


def _schedule_tourist(landmarks: list[Landmark3D], home: tuple[float, float]) -> list[ScheduleStop]:
    stops = [ScheduleStop(9, 0, home[0], home[1], "home")]
    hour = 10
    for lm in landmarks[:6]:
        stops.append(ScheduleStop(hour, 0, lm.x, lm.z, lm.name))
        hour += 2
    stops.append(ScheduleStop(18, 0, home[0], home[1], "home"))
    return stops


def spawn_npcs(
    streets: StreetNetwork,
    landmarks: list[Landmark3D],
    spawn_x: float,
    spawn_z: float,
    count: int = 24,
    seed: int = 7,
) -> list[NPC]:
    rng = random.Random(seed)
    nodes = list(streets.positions.items())
    if not nodes:
        return []

    cafes = _pick_by_kind(landmarks, CAFE) or landmarks
    stores = _pick_by_kind(landmarks, STORE) or landmarks
    parks = _pick_by_kind(landmarks, PARK) or landmarks
    subways = _pick_by_kind(landmarks, SUBWAY)
    sights = _pick_by_kind(landmarks, LANDMARK) or landmarks

    def pick_lm(pool: list[Landmark3D], fallback: tuple[float, float]) -> tuple[float, float]:
        if pool:
            lm = rng.choice(pool)
            return lm.x, lm.z
        return fallback

    home = (spawn_x, spawn_z)
    work = pick_lm(sights, (spawn_x + 80, spawn_z - 60))
    subway = pick_lm(subways, (spawn_x - 40, spawn_z + 30))
    lunch = pick_lm(cafes, pick_lm(stores, home))

    npcs: list[NPC] = []
    personalities = ["commuter", "commuter", "tourist", "local"]
    colors = [(0.8, 0.3, 0.3), (0.3, 0.5, 0.8), (0.9, 0.7, 0.2), (0.4, 0.7, 0.4)]

    for i in range(count):
        nid, (nx, nz) = rng.choice(nodes)
        personality = personalities[i % len(personalities)]
        if personality == "commuter":
            schedule = _schedule_commuter(home, work, subway, lunch)
        elif personality == "tourist":
            schedule = _schedule_tourist(sights, (nx, nz))
        else:
            schedule = [
                ScheduleStop(9, 0, nx, nz, "home"),
                ScheduleStop(11, 0, *pick_lm(cafes, (nx, nz)), "cafe"),
                ScheduleStop(14, 0, *pick_lm(parks, (nx, nz)), "park"),
                ScheduleStop(16, 0, *pick_lm(stores, (nx, nz)), "store"),
                ScheduleStop(19, 0, nx, nz, "home"),
            ]

        npcs.append(
            NPC(
                name=f"npc_{i}",
                personality=personality,
                x=nx,
                z=nz,
                speed=rng.uniform(1.2, 1.8),
                schedule=schedule,
                color=colors[i % len(colors)],
            )
        )
    return npcs

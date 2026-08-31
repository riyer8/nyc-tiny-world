"""Subway graph, stations, and travel simulation."""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nyc_world.core.projection import GeoProjection

from nyc_world.geo.coords import gps_to_world_xz


@dataclass(frozen=True)
class Station:
    id: str
    name: str
    lines: list[str]
    entrance_xz: tuple[float, float]
    latlon: tuple[float, float]

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lines": list(self.lines),
            "entrance_xz": list(self.entrance_xz),
            "latlon": list(self.latlon),
        }

    @classmethod
    def from_dict(cls, data: dict) -> Station:
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            lines=list(data.get("lines", [])),
            entrance_xz=tuple(data.get("entrance_xz", (0.0, 0.0))),
            latlon=tuple(data.get("latlon", (0.0, 0.0))),
        )


# Washington Square area — real-ish coordinates for GPS round-trip tests.
STATION_DEFS: list[tuple[str, str, list[str], float, float]] = [
    ("w4", "West 4th St", ["A", "B", "C", "D", "E", "F", "M"], 40.7323, -74.0020),
    ("14st", "14th St", ["1", "2", "3", "L"], 40.7340, -74.0005),
    ("union_sq", "Union Sq", ["4", "5", "6", "L", "N", "Q", "R", "W"], 40.7357, -73.9909),
    ("astor_pl", "Astor Pl", ["6"], 40.7301, -73.9911),
    ("canal", "Canal St", ["6", "J", "N", "Q", "R", "W", "Z"], 40.7224, -73.9982),
    ("city_hall", "City Hall", ["4", "5", "6", "J", "Z"], 40.7130, -74.0069),
]

EDGE_DEFS: list[tuple[str, str, float]] = [
    ("w4", "14st", 18.0),
    ("14st", "union_sq", 22.0),
    ("w4", "union_sq", 40.0),
    ("union_sq", "astor_pl", 20.0),
    ("astor_pl", "w4", 25.0),
    ("union_sq", "canal", 35.0),
    ("canal", "city_hall", 30.0),
    ("w4", "canal", 45.0),
    ("14st", "astor_pl", 28.0),
]


@dataclass
class SubwayGraph:
    stations: dict[str, Station]
    edges: list[tuple[str, str, float]]

    def neighbors(self, station_id: str) -> list[tuple[str, float]]:
        results: list[tuple[str, float]] = []
        for a, b, t in self.edges:
            if a == station_id:
                results.append((b, t))
            elif b == station_id:
                results.append((a, t))
        return results

    def route(self, origin_id: str, dest_id: str) -> tuple[list[str], float]:
        if origin_id == dest_id:
            return [origin_id], 0.0
        if origin_id not in self.stations or dest_id not in self.stations:
            return [], float("inf")

        dist: dict[str, float] = {origin_id: 0.0}
        prev: dict[str, str | None] = {origin_id: None}
        heap: list[tuple[float, str]] = [(0.0, origin_id)]

        while heap:
            cost, node = heapq.heappop(heap)
            if cost > dist.get(node, float("inf")):
                continue
            if node == dest_id:
                break
            for nxt, edge_t in self.neighbors(node):
                new_cost = cost + edge_t
                if new_cost < dist.get(nxt, float("inf")):
                    dist[nxt] = new_cost
                    prev[nxt] = node
                    heapq.heappush(heap, (new_cost, nxt))

        if dest_id not in dist:
            return [], float("inf")

        path: list[str] = []
        cur: str | None = dest_id
        while cur is not None:
            path.append(cur)
            cur = prev.get(cur)
        path.reverse()
        return path, dist[dest_id]

    def nearest_station(self, x: float, z: float) -> str | None:
        best: str | None = None
        best_d = float("inf")
        for sid, station in self.stations.items():
            dx = station.entrance_xz[0] - x
            dz = station.entrance_xz[1] - z
            d = dx * dx + dz * dz
            if d < best_d:
                best_d = d
                best = sid
        return best

    def line_diagram(self, *, highlight: list[str] | None = None) -> list[str]:
        order = ["w4", "14st", "union_sq", "astor_pl", "canal", "city_hall"]
        labels = []
        for sid in order:
            if sid not in self.stations:
                continue
            name = self.stations[sid].name.split()[0]
            if highlight and sid in highlight:
                labels.append(f"●{name}")
            else:
                labels.append(f"○{name}")
        return [" ".join(labels)]

    def menu_lines(self, origin_id: str) -> list[str]:
        origin = self.stations.get(origin_id)
        if not origin:
            return ["Unknown station."]
        lines = [
            f"ENTER SUBWAY — {origin.name}",
            "─" * 28,
            *self.line_diagram(highlight=[origin_id]),
            "",
            "Select destination:",
        ]
        idx = 1
        for sid, station in self.stations.items():
            if sid == origin_id:
                continue
            route, seconds = self.route(origin_id, sid)
            if not route:
                continue
            mins = max(1, int(round(seconds / 60))) if seconds >= 60 else int(round(seconds))
            unit = "min" if seconds >= 60 else "sec"
            lines.append(f"  [{idx}] {station.name} ({mins} {unit})")
            idx += 1
        lines.append("  [Esc] Cancel")
        return lines

    def destination_ids(self, origin_id: str) -> list[str]:
        return [sid for sid in self.stations if sid != origin_id]


def build_subway_graph(projection: GeoProjection | None = None) -> SubwayGraph:
    stations: dict[str, Station] = {}
    for sid, name, lines, lat, lon in STATION_DEFS:
        if projection:
            x, z = gps_to_world_xz(lat, lon, projection)
        else:
            x, z = _fallback_xz(sid)
        stations[sid] = Station(
            id=sid,
            name=name,
            lines=lines,
            entrance_xz=(x, z),
            latlon=(lat, lon),
        )
    return SubwayGraph(stations=stations, edges=list(EDGE_DEFS))


def _fallback_xz(station_id: str) -> tuple[float, float]:
    offsets = {
        "w4": (0.0, 0.0),
        "14st": (40.0, 20.0),
        "union_sq": (120.0, 30.0),
        "astor_pl": (100.0, -40.0),
        "canal": (-60.0, -80.0),
        "city_hall": (-140.0, -160.0),
    }
    return offsets.get(station_id, (0.0, 0.0))


@dataclass
class SubwayRide:
    rider_id: str
    origin_id: str
    dest_id: str
    route: list[str]
    duration_s: float
    elapsed_s: float = 0.0
    complete: bool = False

    @property
    def progress(self) -> float:
        if self.duration_s <= 0:
            return 1.0
        return min(1.0, self.elapsed_s / self.duration_s)


@dataclass
class SubwaySimulation:
    graph: SubwayGraph
    active_rides: list[SubwayRide] = field(default_factory=list)
    npc_ride_count: int = 0
    commuter_count: int = 0

    def travel_time(self, origin_id: str, dest_id: str) -> float:
        _, seconds = self.graph.route(origin_id, dest_id)
        return seconds

    def start_ride(self, rider_id: str, origin_id: str, dest_id: str) -> SubwayRide | None:
        route, seconds = self.graph.route(origin_id, dest_id)
        if not route or seconds == float("inf"):
            return None
        ride = SubwayRide(
            rider_id=rider_id,
            origin_id=origin_id,
            dest_id=dest_id,
            route=route,
            duration_s=seconds,
        )
        self.active_rides.append(ride)
        return ride

    def update(self, dt: float) -> list[SubwayRide]:
        finished: list[SubwayRide] = []
        for ride in self.active_rides:
            if ride.complete:
                continue
            ride.elapsed_s += dt
            if ride.elapsed_s >= ride.duration_s:
                ride.complete = True
                finished.append(ride)
        self.active_rides = [r for r in self.active_rides if not r.complete]
        return finished

    def exit_position(self, ride: SubwayRide) -> tuple[float, float]:
        station = self.graph.stations[ride.dest_id]
        return station.entrance_xz

    def try_npc_ride(
        self,
        npc,
        *,
        target_x: float,
        target_z: float,
        is_raining: bool,
        min_distance: float = 120.0,
    ) -> bool:
        if npc.personality != "commuter":
            return False
        dist = math.hypot(target_x - npc.x, target_z - npc.z)
        if not is_raining and dist < min_distance:
            return False
        if is_raining and dist < 60.0:
            return False

        origin = self.graph.nearest_station(npc.x, npc.z)
        if not origin:
            return False
        dest = self.graph.nearest_station(target_x, target_z)
        if not dest or dest == origin:
            return False
        _, seconds = self.graph.route(origin, dest)
        if seconds == float("inf"):
            return False

        sx, sz = self.graph.stations[dest].entrance_xz
        npc.x, npc.z = sx, sz
        npc.path = []
        npc.path_index = 0
        npc.agent_action = "subway"
        self.npc_ride_count += 1
        return True

    def commuter_subway_rate(self) -> float:
        if self.commuter_count <= 0:
            return 0.0
        return self.npc_ride_count / self.commuter_count

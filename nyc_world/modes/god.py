"""God / sandbox mode — direct city patches and laboratory controls."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nyc_world.city.world_clock import Weather
from nyc_world.feeds.types import CityEvent

if TYPE_CHECKING:
    from nyc_world.city.city_sim import CitySimulation
    from nyc_world.simulation.event_log import EventLog


def _edge_key(u: int, v: int) -> tuple[int, int]:
    return (min(u, v), max(u, v))


@dataclass
class GodPatch:
    """Live patches applied directly to the running city simulation."""

    time_hour: int | None = None
    time_minute: int | None = None
    weather_override: str | None = None
    active_events: list[CityEvent] = field(default_factory=list)
    road_closures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "time_hour": self.time_hour,
            "time_minute": self.time_minute,
            "weather_override": self.weather_override,
            "active_events": [e.to_dict() for e in self.active_events],
            "road_closures": list(self.road_closures),
        }

    @classmethod
    def from_dict(cls, data: dict) -> GodPatch:
        return cls(
            time_hour=data.get("time_hour"),
            time_minute=data.get("time_minute"),
            weather_override=data.get("weather_override"),
            active_events=[CityEvent.from_dict(e) for e in data.get("active_events", [])],
            road_closures=list(data.get("road_closures", [])),
        )


@dataclass
class GodMode:
    active: bool = False
    patch: GodPatch = field(default_factory=GodPatch)
    blocked_edges: set[tuple[int, int]] = field(default_factory=set)
    festival_active: bool = False
    festival_npc_ids: list[str] = field(default_factory=list)
    baseline_npc_count: int = 0

    def toggle(self) -> bool:
        self.active = not self.active
        return self.active

    def hud_lines(self, city) -> list[str]:
        clock = city.clock
        lines = [
            "⚡ CITY LABORATORY",
            "─" * 28,
            f"Time   {clock.time_str}  (6/12/0 presets)",
            f"Weather {clock.weather.value}",
            f"Events  {len(self.patch.active_events)} active",
            f"Road closures  {len(self.blocked_edges)}",
            f"NPCs  {len(city.npcs)}  (+{len(self.festival_npc_ids)} festival)",
            "",
            "` exit · 6/1/0 time · W rain · D clear · V festival · C close road · X clear",
        ]
        for event in self.patch.active_events[-3:]:
            lines.append(f"  · {event.title}")
        return lines

    def crowd_boost_pct(self) -> float:
        if not self.festival_active:
            return 0.0
        return 0.2 * len(self.festival_npc_ids)

    def apply_time(self, city: CitySimulation, hour: int, minute: int = 0, *, event_log: EventLog | None = None) -> None:
        city.clock.hour = hour % 24
        city.clock.minute = minute % 60
        self.patch.time_hour = hour
        self.patch.time_minute = minute
        if event_log:
            event_log.append(
                tick=getattr(city, "_tick", 0),
                game_day=city.clock.day,
                game_time=city.clock.time_str,
                actor_id="god",
                action="set_time",
                location_id="city",
                details=f"{hour:02d}:{minute:02d}",
            )

    def apply_weather(self, city: CitySimulation, weather: str, *, event_log: EventLog | None = None) -> None:
        alias = {"snow": "cloudy"}
        key = alias.get(weather, weather)
        try:
            city.clock.set_feed_weather(Weather(key))
        except ValueError:
            city.clock.weather = Weather.CLEAR
        self.patch.weather_override = weather
        if event_log:
            event_log.append(
                tick=getattr(city, "_tick", 0),
                game_day=city.clock.day,
                game_time=city.clock.time_str,
                actor_id="god",
                action="set_weather",
                location_id="city",
                details=weather,
            )

    def spawn_festival(
        self,
        city: CitySimulation,
        x: float,
        z: float,
        *,
        count: int = 6,
        event_log: EventLog | None = None,
    ) -> int:
        from nyc_world.city.npcs import NPC, ScheduleStop

        if not self.festival_active:
            self.baseline_npc_count = len(city.npcs)
        rng = random.Random(99)
        spawned = 0
        for i in range(count):
            vid = f"vendor_{len(city.npcs)}"
            vx = x + rng.uniform(-15, 15)
            vz = z + rng.uniform(-15, 15)
            npc = NPC(
                vid,
                "pedestrian",
                vx,
                vz,
                1.1,
                [ScheduleStop(12, 0, vx, vz, "festival")],
                color=(0.9, 0.5, 0.2),
            )
            city.npcs.append(npc)
            self.festival_npc_ids.append(vid)
            spawned += 1
        self.festival_active = True
        event = CityEvent(title="Village Festival", location="street", start_hour=city.clock.hour)
        self.patch.active_events.append(event)
        city.feed_modifiers.sidewalk_density_near_station = max(
            city.feed_modifiers.sidewalk_density_near_station, 0.2
        )
        if event_log:
            event_log.append(
                tick=getattr(city, "_tick", 0),
                game_day=city.clock.day,
                game_time=city.clock.time_str,
                actor_id="god",
                action="spawn_festival",
                location_id="street",
                details=f"+{spawned} vendors",
            )
        return spawned

    def close_road(self, city: CitySimulation, *, event_log: EventLog | None = None) -> bool:
        streets = city.streets
        if not streets or not streets.drive_graph:
            return False
        for u, neighbors in streets.drive_graph.items():
            for v, _ in neighbors:
                key = _edge_key(u, v)
                if key not in self.blocked_edges:
                    self.blocked_edges.add(key)
                    streets.blocked_edges.add(key)
                    closure_id = f"{u}:{v}"
                    self.patch.road_closures.append(closure_id)
                    self._invalidate_vehicle_routes(city)
                    if event_log:
                        event_log.append(
                            tick=getattr(city, "_tick", 0),
                            game_day=city.clock.day,
                            game_time=city.clock.time_str,
                            actor_id="god",
                            action="road_closure",
                            location_id=closure_id,
                        )
                    return True
        return False

    @staticmethod
    def _invalidate_vehicle_routes(city: CitySimulation) -> None:
        for vehicle in getattr(city, "vehicles", []):
            vehicle.path = []
            vehicle.path_index = 0
            vehicle.wait = 0.0

    def clear_road_closures(self, city: CitySimulation, *, event_log: EventLog | None = None) -> None:
        if city.streets:
            city.streets.blocked_edges.clear()
        self.blocked_edges.clear()
        self.patch.road_closures.clear()
        if event_log:
            event_log.append(
                tick=getattr(city, "_tick", 0),
                game_day=city.clock.day,
                game_time=city.clock.time_str,
                actor_id="god",
                action="clear_closures",
                location_id="city",
            )

    def remove_festival(self, city: CitySimulation) -> None:
        city.npcs = [n for n in city.npcs if n.name not in self.festival_npc_ids]
        self.festival_npc_ids.clear()
        self.festival_active = False
        self.patch.active_events = [
            e for e in self.patch.active_events if e.title != "Village Festival"
        ]
        city.feed_modifiers.sidewalk_density_near_station = max(
            0.0, city.feed_modifiers.sidewalk_density_near_station - 0.2
        )

    def apply_to_city(self, city: CitySimulation, *, event_log: EventLog | None = None) -> None:
        if self.patch.time_hour is not None:
            self.apply_time(city, self.patch.time_hour, self.patch.time_minute or 0, event_log=event_log)
        if self.patch.weather_override:
            self.apply_weather(city, self.patch.weather_override, event_log=event_log)
        if city.streets:
            city.streets.blocked_edges = set(self.blocked_edges)

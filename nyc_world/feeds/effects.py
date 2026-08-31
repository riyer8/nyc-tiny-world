"""Translate feed alerts into simulation parameter modifiers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulationModifiers:
    subway_boarding_rate: float = 1.0
    bus_route_weight: float = 1.0
    sidewalk_density_near_station: float = 0.0
    cafe_occupancy_boost: float = 0.0
    umbrella_probability: float = 0.0
    weather_override: str | None = None
    transit_affected_npcs: int = 0
    debug_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "subway_boarding_rate": self.subway_boarding_rate,
            "bus_route_weight": self.bus_route_weight,
            "sidewalk_density_near_station": self.sidewalk_density_near_station,
            "cafe_occupancy_boost": self.cafe_occupancy_boost,
            "umbrella_probability": self.umbrella_probability,
            "weather_override": self.weather_override,
            "transit_affected_npcs": self.transit_affected_npcs,
            "debug_notes": list(self.debug_notes),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SimulationModifiers:
        return cls(
            subway_boarding_rate=data.get("subway_boarding_rate", 1.0),
            bus_route_weight=data.get("bus_route_weight", 1.0),
            sidewalk_density_near_station=data.get("sidewalk_density_near_station", 0.0),
            cafe_occupancy_boost=data.get("cafe_occupancy_boost", 0.0),
            umbrella_probability=data.get("umbrella_probability", 0.0),
            weather_override=data.get("weather_override"),
            transit_affected_npcs=data.get("transit_affected_npcs", 0),
            debug_notes=list(data.get("debug_notes", [])),
        )


def modifiers_from_feed(state: CityFeedState) -> SimulationModifiers:
    mods = SimulationModifiers()
    if state.weather:
        mods.weather_override = state.weather.condition
        if state.weather.condition == "rain":
            mods.umbrella_probability = 0.65
        mods.debug_notes.append(state.weather.summary)

    for alert in state.transit:
        if alert.delay_minutes <= 0:
            continue
        severity = min(1.0, alert.delay_minutes / 30.0)
        mods.subway_boarding_rate = min(mods.subway_boarding_rate, 1.0 - 0.4 * severity)
        mods.bus_route_weight = max(mods.bus_route_weight, 1.0 + 0.3 * severity)
        mods.sidewalk_density_near_station = max(
            mods.sidewalk_density_near_station, 0.2 * severity
        )
        mods.cafe_occupancy_boost = max(mods.cafe_occupancy_boost, 0.15 * severity)
        mods.debug_notes.append(alert.summary)

    for event in state.events:
        mods.debug_notes.append(f"{event.title} @ {event.location}")

    return mods


def apply_score_modifiers(
    scores: dict[str, float],
    mods: SimulationModifiers,
    *,
    near_subway: bool,
    near_cafe: bool,
) -> dict[str, float]:
    """Bias utility scores based on active feed modifiers."""
    adjusted = dict(scores)
    if near_subway and mods.sidewalk_density_near_station > 0:
        linger = mods.sidewalk_density_near_station
        adjusted["wander"] = adjusted.get("wander", 0.0) + linger * 0.5
        adjusted["socialize"] = adjusted.get("socialize", 0.0) + linger * 0.3
        if mods.subway_boarding_rate < 1.0:
            adjusted["explore"] = adjusted.get("explore", 0.0) - (1.0 - mods.subway_boarding_rate) * 0.4

    if near_cafe and mods.cafe_occupancy_boost > 0:
        adjusted["eat"] = adjusted.get("eat", 0.0) + mods.cafe_occupancy_boost
        adjusted["socialize"] = adjusted.get("socialize", 0.0) + mods.cafe_occupancy_boost * 0.5

    return adjusted


def count_transit_affected_npcs(
    npc_positions: dict[str, tuple[float, float]],
    subway_positions: list[tuple[float, float]],
    mods: SimulationModifiers,
    *,
    radius_m: float = 45.0,
) -> int:
    if mods.sidewalk_density_near_station <= 0 or not subway_positions:
        return 0
    radius_sq = radius_m * radius_m
    count = 0
    for x, z in npc_positions.values():
        for sx, sz in subway_positions:
            dx, dz = x - sx, z - sz
            if dx * dx + dz * dz <= radius_sq:
                count += 1
                break
    return count


def banner_lines(state: CityFeedState) -> list[str]:
    lines: list[str] = []
    for alert in state.transit:
        if alert.summary:
            lines.append(f"🚇 {alert.summary}")
        else:
            lines.append(f"🚇 {alert.line} train delayed {alert.delay_minutes} min")
    if state.weather and state.weather.summary:
        icon = "🌧️" if state.weather.condition == "rain" else "🌤️"
        lines.append(f"{icon}  {state.weather.summary}")
    for event in state.events[:2]:
        lines.append(f"📅 {event.title}")
    return lines

"""Hypothetical world patches for what-if simulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.simulation.state import WorldState


@dataclass
class WorldPatch:
    """Inject hypothetical changes before rolling forward."""

    weather_override: str | None = None
    weather_at_hour: int | None = None
    transit_line: str | None = None
    transit_shutdown: bool = False
    relationship_overrides: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "weather_override": self.weather_override,
            "weather_at_hour": self.weather_at_hour,
            "transit_line": self.transit_line,
            "transit_shutdown": self.transit_shutdown,
            "relationship_overrides": dict(self.relationship_overrides),
        }

    @classmethod
    def from_dict(cls, data: dict) -> WorldPatch:
        return cls(
            weather_override=data.get("weather_override"),
            weather_at_hour=data.get("weather_at_hour"),
            transit_line=data.get("transit_line"),
            transit_shutdown=data.get("transit_shutdown", False),
            relationship_overrides=dict(data.get("relationship_overrides", {})),
        )


def apply_patch(state: WorldState, patch: WorldPatch | None) -> WorldState:
    """Return a copy of state with patch fields applied immediately."""
    if not patch:
        return WorldState.from_dict(state.to_dict())
    patched = WorldState.from_dict(state.to_dict())
    if patch.weather_override and patch.weather_at_hour is None:
        patched.clock.weather = patch.weather_override
    for npc_id, affinity in patch.relationship_overrides.items():
        npc = patched.npc_by_id(npc_id)
        if npc:
            npc.player_affinity = affinity
            npc.trust = max(0.0, affinity * 100.0)
        if npc_id in patched.player.relationships:
            patched.player.relationships[npc_id] = affinity
    return patched

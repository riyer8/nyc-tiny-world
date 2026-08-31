"""Roll-forward imagination using a trained world model."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from nyc_world.simulation.actions import Action, PlayerMoveAction, WaitAction
from nyc_world.simulation.encoding import encode_input
from nyc_world.simulation.model.simple_model import WorldModel, apply_prediction
from nyc_world.simulation.model.world_patch import WorldPatch, apply_patch
from nyc_world.simulation.state import NPCState, WorldState

# Approximate Washington Square zone centers (world meters).
PARK_ZONE = (80.0, 10.0)
CAFE_ZONE = (30.0, -20.0)
SUBWAY_ZONE = (-40.0, 30.0)
ZONE_RADIUS = 45.0


@dataclass
class ZoneMetrics:
    hour: int
    minute: int
    weather: str
    park_npcs: int
    cafe_npcs: int
    vehicle_count: int
    subway_nearby: int

    def label(self) -> str:
        return f"{self.hour:02d}:{self.minute:02d}  {self.weather}"

    def summary(self) -> str:
        return (
            f"park {self.park_npcs}  cafe {self.cafe_occupancy_pct()}%  "
            f"vehicles {self.vehicle_count}"
        )

    def cafe_occupancy_pct(self) -> int:
        return min(100, self.cafe_npcs * 18)


@dataclass
class WhatIfResult:
    baseline: list[ZoneMetrics] = field(default_factory=list)
    predicted: list[ZoneMetrics] = field(default_factory=list)
    diff_lines: list[str] = field(default_factory=list)


def _count_near(state: WorldState, cx: float, cz: float, radius: float = ZONE_RADIUS) -> int:
    radius_sq = radius * radius
    count = 0
    for npc in state.npcs:
        dx, dz = npc.x - cx, npc.z - cz
        if dx * dx + dz * dz <= radius_sq:
            count += 1
    return count


def compute_zone_metrics(state: WorldState) -> ZoneMetrics:
    return ZoneMetrics(
        hour=state.clock.hour,
        minute=state.clock.minute,
        weather=state.clock.weather,
        park_npcs=_count_near(state, *PARK_ZONE),
        cafe_npcs=_count_near(state, *CAFE_ZONE),
        vehicle_count=state.vehicle_count or len(state.vehicles),
        subway_nearby=_count_near(state, *SUBWAY_ZONE, radius=35.0),
    )


def _weather_at(state: WorldState, patch: WorldPatch | None) -> str:
    if not patch or not patch.weather_override or patch.weather_at_hour is None:
        return state.clock.weather
    hour = state.clock.hour + state.clock.minute / 60.0
    if hour >= patch.weather_at_hour:
        return patch.weather_override
    return state.clock.weather


def _rule_step(
    state: WorldState,
    *,
    minutes: int,
    patch: WorldPatch | None,
    rng: random.Random,
) -> WorldState:
    nxt = WorldState.from_dict(state.to_dict())
    total = state.clock.hour * 60 + state.clock.minute + minutes
    nxt.clock.hour = int(total // 60) % 24
    nxt.clock.minute = int(total % 60)
    nxt.tick = state.tick + 1
    nxt.clock.tick = nxt.tick

    weather = _weather_at(nxt, patch)
    nxt.clock.weather = weather
    raining = weather == "rain"
    transit_down = bool(patch and patch.transit_shutdown)

    for npc in nxt.npcs:
        dist_park = math.hypot(npc.x - PARK_ZONE[0], npc.z - PARK_ZONE[1])
        dist_cafe = math.hypot(npc.x - CAFE_ZONE[0], npc.z - CAFE_ZONE[1])
        dist_subway = math.hypot(npc.x - SUBWAY_ZONE[0], npc.z - SUBWAY_ZONE[1])

        if raining and dist_park < ZONE_RADIUS:
            if rng.random() < 0.85:
                npc.x += (npc.x - PARK_ZONE[0]) * 0.4 + rng.uniform(-3, 3)
                npc.z += (npc.z - PARK_ZONE[1]) * 0.4 + rng.uniform(-3, 3)
        elif transit_down and dist_subway < 40 and rng.random() < 0.35:
            npc.x += (CAFE_ZONE[0] - npc.x) * 0.12
            npc.z += (CAFE_ZONE[1] - npc.z) * 0.12
        elif dist_cafe > ZONE_RADIUS * 2:
            npc.x += rng.uniform(-1.5, 1.5)
            npc.z += rng.uniform(-1.5, 1.5)

    if transit_down:
        nxt.vehicle_count = max(0, nxt.vehicle_count - 1)

    return nxt


def rule_based_timeline(
    initial: WorldState,
    patch: WorldPatch | None,
    *,
    horizon_minutes: int = 30,
    step_minutes: int = 15,
    seed: int = 42,
) -> list[ZoneMetrics]:
    rng = random.Random(seed + _patch_key(patch))
    state = apply_patch(initial, patch)
    steps = max(1, horizon_minutes // step_minutes)
    timeline = [compute_zone_metrics(state)]
    for _ in range(steps):
        state = _rule_step(state, minutes=step_minutes, patch=patch, rng=rng)
        timeline.append(compute_zone_metrics(state))
    return timeline


def _patch_key(patch: WorldPatch | None) -> int:
    if not patch:
        return 0
    return hash(
        (
            patch.weather_override,
            patch.weather_at_hour,
            patch.transit_line,
            patch.transit_shutdown,
            tuple(sorted(patch.relationship_overrides.items())),
        )
    )


def run_what_if(
    initial: WorldState,
    patch: WorldPatch,
    *,
    horizon_minutes: int = 30,
    step_minutes: int = 15,
    seed: int = 42,
) -> WhatIfResult:
    """Compare baseline vs patched rule-based timelines."""
    baseline = rule_based_timeline(
        initial, None, horizon_minutes=horizon_minutes, step_minutes=step_minutes, seed=seed
    )
    predicted = rule_based_timeline(
        initial, patch, horizon_minutes=horizon_minutes, step_minutes=step_minutes, seed=seed
    )
    diff = diff_hud_lines(baseline, predicted)
    return WhatIfResult(baseline=baseline, predicted=predicted, diff_lines=diff)


def diff_hud_lines(baseline: list[ZoneMetrics], predicted: list[ZoneMetrics]) -> list[str]:
    lines = [
        "REAL (left)          PREDICTED (right)",
        "─" * 40,
    ]
    for base, pred in zip(baseline, predicted):
        left = f"{base.label():>12}  {base.summary()}"
        right = f"{pred.label():>12}  {pred.summary()}"
        if base.park_npcs != pred.park_npcs:
            right = right.replace(f"park {pred.park_npcs}", f"park {pred.park_npcs} 🌧️" if pred.weather == "rain" else f"park {pred.park_npcs}")
        lines.append(f"{left:<26} {right}")
    return lines


def format_what_if_report(result: WhatIfResult, *, title: str = "WHAT IF") -> list[str]:
    lines = [f"🔮 {title}", "=" * 40]
    lines.extend(result.diff_lines)
    return lines


def seed_npc_positions(
    state: WorldState,
    *,
    park_count: int = 8,
    cafe_count: int = 4,
) -> WorldState:
    """Place synthetic NPCs for what-if demos when state has few NPCs."""
    if len(state.npcs) >= park_count:
        return state
    seeded = WorldState.from_dict(state.to_dict())
    rng = random.Random(7)
    for i in range(park_count):
        angle = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0, ZONE_RADIUS * 0.8)
        seeded.npcs.append(
            NPCState(
                id=f"park_npc_{i}",
                name=f"park_npc_{i}",
                x=PARK_ZONE[0] + math.cos(angle) * r,
                z=PARK_ZONE[1] + math.sin(angle) * r,
            )
        )
    for i in range(cafe_count):
        seeded.npcs.append(
            NPCState(
                id=f"cafe_npc_{i}",
                name=f"cafe_npc_{i}",
                x=CAFE_ZONE[0] + rng.uniform(-10, 10),
                z=CAFE_ZONE[1] + rng.uniform(-10, 10),
            )
        )
    seeded.npc_count = len(seeded.npcs)
    return seeded


def roll_forward(
    model: WorldModel,
    initial_state: WorldState,
    actions: list[Action],
) -> list[WorldState]:
    """Imagine a future trajectory without running the real simulation."""
    trajectory = [initial_state]
    current = initial_state
    for action in actions:
        features = encode_input(current, action)
        prediction = model.predict(features)
        current = apply_prediction(current, prediction)
        trajectory.append(current)
    return trajectory


def describe_trajectory(states: list[WorldState]) -> list[str]:
    """Human-readable summary of an imagined future."""
    lines: list[str] = []
    for i, state in enumerate(states):
        maya = state.npc_by_id("maya")
        alex = state.npc_by_id("alex")
        maya_pos = f"({maya.x:.0f},{maya.z:.0f})" if maya else "?"
        alex_pos = f"({alex.x:.0f},{alex.z:.0f})" if alex else "?"
        lines.append(
            f"t+{i}: player=({state.player.x:.0f},{state.player.z:.0f}) "
            f"time={state.clock.hour:02d}:{state.clock.minute:02d} "
            f"weather={state.clock.weather} "
            f"maya={maya_pos} alex={alex_pos}"
        )
    return lines


def default_explore_actions(steps: int, *, north: bool = True) -> list[Action]:
    """Generate a simple walk-north action sequence for demos."""
    dx, dz = (0.0, 2.0) if north else (2.0, 0.0)
    return [PlayerMoveAction(dx=dx, dz=dz) for _ in range(steps)] + [WaitAction()]

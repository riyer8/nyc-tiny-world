"""Tests for what-if imagination engine."""

from __future__ import annotations

from nyc_world.simulation.model.imagination import (
    compute_zone_metrics,
    rule_based_timeline,
    run_what_if,
    seed_npc_positions,
)
from nyc_world.simulation.model.world_patch import WorldPatch, apply_patch
from nyc_world.simulation.state import ClockState, WorldState


def _park_state() -> WorldState:
    state = WorldState(clock=ClockState(hour=16, minute=30, weather="clear"))
    return seed_npc_positions(state, park_count=10, cafe_count=3)


def test_apply_patch_weather_and_relationship():
    state = _park_state()
    patch = WorldPatch(
        weather_override="rain",
        relationship_overrides={"maya": 0.0},
    )
    patched = apply_patch(state, patch)
    assert patched.clock.weather == "rain"
    maya = patched.npc_by_id("maya")
    if maya:
        assert maya.player_affinity == 0.0


def test_rain_what_if_drops_park_occupancy():
    state = _park_state()
    patch = WorldPatch(weather_override="rain", weather_at_hour=17)
    result = run_what_if(state, patch, horizon_minutes=45, step_minutes=15, seed=42)
    rainy_pred = [m for m in result.predicted if m.weather == "rain"]
    assert rainy_pred
    base_at_rain = result.baseline[-1].park_npcs
    pred_at_rain = rainy_pred[-1].park_npcs
    assert pred_at_rain < base_at_rain
    assert any("PREDICTED" in line for line in result.diff_lines)


def test_roll_forward_deterministic_with_seed():
    state = _park_state()
    patch = WorldPatch(weather_override="rain", weather_at_hour=17)
    a = rule_based_timeline(state, patch, seed=99)
    b = rule_based_timeline(state, patch, seed=99)
    assert [m.park_npcs for m in a] == [m.park_npcs for m in b]


def test_diff_hud_side_by_side():
    state = _park_state()
    result = run_what_if(
        state,
        WorldPatch(transit_line="F", transit_shutdown=True),
        horizon_minutes=30,
        step_minutes=15,
        seed=1,
    )
    assert len(result.diff_lines) >= 3
    assert "REAL" in result.diff_lines[0]


def test_compute_zone_metrics_counts_park():
    state = _park_state()
    metrics = compute_zone_metrics(state)
    assert metrics.park_npcs >= 8

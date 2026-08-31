#!/usr/bin/env python3
"""Imagine a future using the world model or rule-based what-if engine."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import gps_to_world_xz
from nyc_world.modes.imagine import SCENARIOS
from nyc_world.simulation.model.imagination import (
    default_explore_actions,
    describe_trajectory,
    format_what_if_report,
    roll_forward,
    run_what_if,
    seed_npc_positions,
)
from nyc_world.simulation.model.simple_model import WorldModel
from nyc_world.simulation.state import ClockState, PlayerState, WorldState


def _build_initial_state(proj: GeoProjection) -> WorldState:
    x, z = gps_to_world_xz(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, proj)
    state = WorldState(
        tick=0,
        clock=ClockState(hour=16, minute=30, weather="clear"),
        player=PlayerState(x=x, z=z, money=37, items={"metro_card": 1}),
        npcs=[],
    )
    return seed_npc_positions(state)


def main() -> None:
    parser = argparse.ArgumentParser(description="Roll forward an imagined future.")
    parser.add_argument(
        "--model",
        type=Path,
        default=Path("data/models/world_model.json"),
        help="Trained model weights",
    )
    parser.add_argument("--steps", type=int, default=10, help="Imagined steps into the future")
    parser.add_argument("--north", action="store_true", help="Walk north each step")
    parser.add_argument("--east", action="store_true", help="Walk east each step")
    parser.add_argument(
        "--what-if",
        choices=[s.scenario_id for s in SCENARIOS],
        help="Run rule-based what-if scenario (shared with in-game imagine mode)",
    )
    args = parser.parse_args()

    proj = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    initial = _build_initial_state(proj)

    if args.what_if:
        scenario = next(s for s in SCENARIOS if s.scenario_id == args.what_if)
        result = run_what_if(initial, scenario.patch, horizon_minutes=30, seed=42)
        for line in format_what_if_report(result, title=scenario.label.upper()):
            print(line)
        return

    if not args.model.exists():
        print(f"Model not found: {args.model}")
        print("Train first: python3 scripts/train_world_model.py")
        print("Or use: python3 scripts/imagine_future.py --what-if rain_at_5pm")
        sys.exit(1)

    model = WorldModel.load(args.model)
    if args.east:
        actions = default_explore_actions(args.steps, north=False)
    else:
        actions = default_explore_actions(args.steps, north=True)

    trajectory = roll_forward(model, initial, actions)

    print("🔮 IMAGINED FUTURE")
    print("=" * 60)
    print(f"Starting at Washington Square ({initial.player.x:.0f}, {initial.player.z:.0f})")
    print()
    for line in describe_trajectory(trajectory):
        print(line)
    print()
    print(f"Imagined {args.steps} steps ahead using {args.model}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Imagine a future using the trained world model."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import gps_to_world_xz
from nyc_world.simulation.model.imagination import (
    default_explore_actions,
    describe_trajectory,
    roll_forward,
)
from nyc_world.simulation.model.simple_model import WorldModel
from nyc_world.simulation.state import ClockState, PlayerState, WorldState


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
    args = parser.parse_args()

    if not args.model.exists():
        print(f"Model not found: {args.model}")
        print("Train first: python3 scripts/train_world_model.py")
        sys.exit(1)

    model = WorldModel.load(args.model)
    proj = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    x, z = gps_to_world_xz(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, proj)

    initial = WorldState(
        tick=0,
        clock=ClockState(hour=14, minute=30, weather="clear"),
        player=PlayerState(x=x, z=z, money=37, items={"metro_card": 1}),
        npcs=[],
    )

    if args.east:
        actions = default_explore_actions(args.steps, north=False)
    else:
        actions = default_explore_actions(args.steps, north=True)

    trajectory = roll_forward(model, initial, actions)

    print("🔮 IMAGINED FUTURE")
    print("=" * 60)
    print(f"Starting at Washington Square ({x:.0f}, {z:.0f})")
    print()
    for line in describe_trajectory(trajectory):
        print(line)
    print()
    print(f"Imagined {args.steps} steps ahead using {args.model}")


if __name__ == "__main__":
    main()

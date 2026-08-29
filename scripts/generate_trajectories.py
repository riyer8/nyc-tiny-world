#!/usr/bin/env python3
"""Generate synthetic trajectories for world-model training (offline demo)."""

from __future__ import annotations

import argparse
from pathlib import Path

import _bootstrap  # noqa: F401

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.areas import WASHINGTON_SQUARE
from nyc_world.core.projection import GeoProjection
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.geo.coords import gps_to_world_xz
from nyc_world.simulation import Simulation
from nyc_world.simulation.actions import PlayerMoveAction, WaitAction


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic trajectory data.")
    parser.add_argument("--steps", type=int, default=200, help="Number of simulation steps")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/trajectories/synthetic.jsonl"),
    )
    args = parser.parse_args()

    proj = GeoProjection.from_area(WASHINGTON_SQUARE, cols=80, rows=80, tile_size=16)
    x, z = gps_to_world_xz(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, proj)
    city = CitySimulation(proj, x, z, npc_count=6, vehicle_count=4)
    player = PlayerProfile()
    quests = QuestManager(player, minds=city.mind_registry)
    sim = Simulation(
        city,
        player,
        quests,
        minds=city.mind_registry,
        record_trajectories=True,
        trajectory_dir=args.output.parent,
    )
    sim.recorder.open(args.output.name)

    state = sim.observe(x, z)
    directions = [
        PlayerMoveAction(dx=1.5, dz=0.0),
        PlayerMoveAction(dx=0.0, dz=1.5),
        PlayerMoveAction(dx=-1.5, dz=0.0),
        PlayerMoveAction(dx=0.0, dz=-1.5),
        WaitAction(),
    ]

    for i in range(args.steps):
        action = directions[i % len(directions)]
        if isinstance(action, PlayerMoveAction):
            x += action.dx
            z += action.dz
        sim.advance_world(1 / 60)
        sim.tick += 1
        next_state = sim.observe(x, z)
        sim.record_transition(state, action, next_state)
        state = next_state

    sim.close()
    print(f"Wrote {args.steps} steps to {args.output}")


if __name__ == "__main__":
    main()

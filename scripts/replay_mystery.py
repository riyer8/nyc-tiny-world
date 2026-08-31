#!/usr/bin/env python3
"""Replay a procedural mystery backstory from a seed."""

from __future__ import annotations

import argparse
import sys

import _bootstrap  # noqa: F401

from nyc_world.simulation.mystery import generate_mystery


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay mystery backstory timeline")
    parser.add_argument("--seed", type=int, default=42, help="Mystery seed")
    parser.add_argument("--reveal", action="store_true", help="Show hidden culprit events")
    args = parser.parse_args()

    case = generate_mystery(args.seed)
    print(f"=== {case.title} (seed {case.seed}) ===")
    print(f"Victim: {case.victim_id}  Culprit: {case.culprit_id}")
    print(f"Stolen: {case.stolen_item}  Where: {case.crime_location}  When: {case.crime_time}")
    print()
    print("BACKSTORY TIMELINE")
    for entry in case.backstory_log.entries:
        if entry.visibility == "hidden" and not args.reveal:
            continue
        vis = f" [{entry.visibility}]" if entry.visibility != "public" else ""
        detail = f" — {entry.details}" if entry.details else ""
        print(
            f"  {entry.game_time:>8}  {entry.actor_id:12}  {entry.action:8}  "
            f"{entry.location_id}{detail}{vis}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Train a lightweight world model from recorded trajectories."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from nyc_world.simulation.model import train_from_directory


def main() -> None:
    parser = argparse.ArgumentParser(description="Train world model from trajectories.")
    parser.add_argument(
        "--data",
        type=Path,
        default=Path("data/trajectories"),
        help="Directory with .jsonl trajectory files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/models/world_model.json"),
        help="Where to save trained model weights",
    )
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--lr", type=float, default=0.02)
    args = parser.parse_args()

    if not args.data.exists() or not list(args.data.glob("*.jsonl")):
        print("No trajectories found. Run:")
        print("  python3 scripts/generate_trajectories.py")
        print("  python3 scripts/play_3d.py --record")
        sys.exit(1)

    model, train_mse, val_mse = train_from_directory(
        args.data,
        model_path=args.output,
        epochs=args.epochs,
        learning_rate=args.lr,
    )
    print(f"Model saved to {args.output}")
    print(f"Train MSE: {train_mse:.6f}")
    print(f"Val MSE:   {val_mse:.6f}")


if __name__ == "__main__":
    main()

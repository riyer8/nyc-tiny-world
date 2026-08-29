#!/usr/bin/env python3
"""Prefetch OSM tiles around a location for offline streaming."""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from nyc_world.core.areas import AREAS, WASHINGTON_SQUARE
from nyc_world.streaming import DEFAULT_RADII, TileDataLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Prefetch OSM tiles for streaming.")
    parser.add_argument(
        "--area",
        default=WASHINGTON_SQUARE.slug,
        choices=sorted(AREAS),
    )
    parser.add_argument(
        "--radius-miles",
        type=float,
        default=DEFAULT_RADII.data_miles,
        help="Prefetch radius in miles (default: 5)",
    )
    args = parser.parse_args()

    area = AREAS[args.area]
    radius_m = args.radius_miles * 1609.344
    loader = TileDataLoader(network=True)
    print(f"Prefetching tiles within {args.radius_miles:.1f} mi of {area.name}...")
    loaded = loader.load_around(area.spawn_lat, area.spawn_lon, radius_m)
    print(f"Loaded {len(loaded)} tiles into {loader.cache_dir}")


if __name__ == "__main__":
    main()

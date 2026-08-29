#!/usr/bin/env python3
"""Download OSM data and generate a playable map from real geography."""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401

from nyc_world.areas import AREAS, GREENWICH_VILLAGE
from nyc_world.map_generator import generate_map
from nyc_world.osm_fetch import fetch_osm
from nyc_world.paths import DEFAULT_MAP_PATH, DEFAULT_META_PATH

DEFAULT_TILE_SIZE = 16


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a game map from OpenStreetMap data.",
    )
    parser.add_argument(
        "--area",
        default=GREENWICH_VILLAGE.slug,
        choices=sorted(AREAS),
        help="Area to import (default: greenwich_village)",
    )
    parser.add_argument("--cols", type=int, default=80, help="Map width in tiles")
    parser.add_argument("--rows", type=int, default=80, help="Map height in tiles")
    parser.add_argument(
        "--tile-size",
        type=int,
        default=DEFAULT_TILE_SIZE,
        help="Pixels per tile",
    )
    parser.add_argument("--output", type=DEFAULT_MAP_PATH, help="Output map file")
    parser.add_argument("--meta", type=DEFAULT_META_PATH, help="Projection metadata file")
    parser.add_argument("--refresh", action="store_true", help="Re-download OSM data")
    args = parser.parse_args()

    area = AREAS[args.area]
    print(f"Fetching OpenStreetMap data for {area.name} ({area.description})...")
    osm_data = fetch_osm(area, refresh=args.refresh)
    print(f"  {len(osm_data.get('elements', [])):,} OSM elements loaded")

    print(f"Generating {args.cols}×{args.rows} tile map...")
    result = generate_map(
        area, osm_data, cols=args.cols, rows=args.rows, tile_size=args.tile_size
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(result.text + "\n")
    result.projection.save(args.meta)

    tile_counts: dict[str, int] = {}
    for char in result.text.replace("\n", ""):
        tile_counts[char] = tile_counts.get(char, 0) + 1

    labels = {
        ".": "sidewalk",
        "B": "buildings",
        "R": "roads",
        "G": "parks",
        "O": "POIs",
        "T": "trees",
        "P": "player spawn",
    }
    print("Tile breakdown:")
    for char, count in sorted(tile_counts.items(), key=lambda x: -x[1]):
        print(f"  {labels.get(char, char)}: {count:,}")

    sx, sy = result.projection.to_game(area.spawn_lat, area.spawn_lon)
    print(
        f"Projection: {result.projection.east_span_m:.0f} m × "
        f"{result.projection.north_span_m:.0f} m"
    )
    print(
        f"Spawn GPS ({area.spawn_lat:.5f}, {area.spawn_lon:.5f}) "
        f"→ game ({sx:.0f}, {sy:.0f})"
    )
    print(f"Wrote {args.output} and {args.meta}")


if __name__ == "__main__":
    main()

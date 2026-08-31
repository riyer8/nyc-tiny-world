#!/usr/bin/env python3
"""Download real NYC building facade photos from Wikimedia Commons."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from nyc_world.map.facade_fetch import fetch_facades, rebuild_manifest
from nyc_world.paths import FACADES_DIR


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch building facade textures from Wikimedia.")
    parser.add_argument(
        "--refresh-osm",
        action="store_true",
        help="Re-download Greenwich Village OSM data before fetching images",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of Wikidata buildings to fetch (for testing)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Re-fetch all Wikidata buildings, not just missing ones",
    )
    parser.add_argument(
        "--rebuild-manifest",
        action="store_true",
        help="Rebuild manifest.json from existing JPG files only",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=FACADES_DIR,
        help="Output directory for images and manifest.json",
    )
    args = parser.parse_args()

    if args.rebuild_manifest:
        manifest = rebuild_manifest(args.output)
        print(f"Rebuilt manifest — {len(manifest)} facades in {args.output}")
        return

    try:
        manifest = fetch_facades(
            out_dir=args.output,
            refresh_osm=args.refresh_osm,
            limit=args.limit,
            missing_only=not args.all,
        )
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Done — {len(manifest)} facade textures in {args.output}")


if __name__ == "__main__":
    main()

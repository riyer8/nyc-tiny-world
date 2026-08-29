"""Tile-based OSM data loader with disk cache."""

from __future__ import annotations

import json
from pathlib import Path

from nyc_world.map.osm_fetch import fetch_osm_bbox
from nyc_world.paths import DATA_DIR
from nyc_world.streaming.tiles import GeoTile, tile_bbox, tiles_within_radius

TILE_CACHE_DIR = DATA_DIR / "tiles"


class TileDataLoader:
    """Load and cache OSM data in ~500 m geographic tiles."""

    def __init__(self, cache_dir: Path | None = None, *, network: bool = True) -> None:
        self.cache_dir = cache_dir or TILE_CACHE_DIR
        self.network = network
        self.loaded: dict[str, dict] = {}

    def tile_path(self, tile: GeoTile) -> Path:
        return self.cache_dir / f"tile_{tile.tile_id}.json"

    def ensure_tile(self, tile: GeoTile, *, fetch: bool | None = None) -> dict | None:
        if tile.tile_id in self.loaded:
            return self.loaded[tile.tile_id]

        path = self.tile_path(tile)
        if path.exists():
            data = json.loads(path.read_text())
            self.loaded[tile.tile_id] = data
            return data

        should_fetch = self.network if fetch is None else fetch
        if not should_fetch:
            return None

        south, west, north, east = tile_bbox(tile)
        data = fetch_osm_bbox(south, west, north, east)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
        self.loaded[tile.tile_id] = data
        return data

    def load_around(self, lat: float, lon: float, radius_m: float) -> set[str]:
        """Ensure all tiles within radius are loaded. Returns tile ids."""
        loaded_ids: set[str] = set()
        for tile in tiles_within_radius(lat, lon, radius_m):
            data = self.ensure_tile(tile)
            if data is not None:
                loaded_ids.add(tile.tile_id)
        return loaded_ids

    def merge_elements(self, tile_ids: set[str] | None = None) -> dict:
        """Merge OSM elements from loaded tiles (dedupe by element id)."""
        ids = tile_ids if tile_ids is not None else set(self.loaded)
        merged: dict[int, dict] = {}
        for tile_id in ids:
            data = self.loaded.get(tile_id)
            if not data:
                continue
            for element in data.get("elements", []):
                merged[element["id"]] = element
        return {"elements": list(merged.values())}

    def unload_outside(self, lat: float, lon: float, radius_m: float) -> None:
        """Drop in-memory tiles outside the data radius to save RAM."""
        keep = {t.tile_id for t in tiles_within_radius(lat, lon, radius_m)}
        for tile_id in list(self.loaded):
            if tile_id not in keep:
                del self.loaded[tile_id]

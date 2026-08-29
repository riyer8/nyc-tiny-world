"""Project paths — data, maps, and generated assets."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MAPS_DIR = PROJECT_ROOT / "maps"
DEFAULT_MAP_PATH = MAPS_DIR / "map.txt"
DEFAULT_META_PATH = MAPS_DIR / "map_meta.json"

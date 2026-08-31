"""Project paths — data, maps, and generated assets."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MAPS_DIR = PROJECT_ROOT / "maps"
SAVES_DIR = DATA_DIR / "saves"
FEEDS_DIR = DATA_DIR / "feeds"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
FACADES_DIR = DATA_DIR / "facades"
MODS_DIR = PROJECT_ROOT / "mods"
DEFAULT_MAP_PATH = MAPS_DIR / "map.txt"
DEFAULT_META_PATH = MAPS_DIR / "map_meta.json"

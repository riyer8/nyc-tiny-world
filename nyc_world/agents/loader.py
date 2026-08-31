"""Discover and load mod NPCs from mods/*.py."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from nyc_world.agents.dialogue import merge_into_game_dialogue
from nyc_world.agents.registry import NPCRegistry
from nyc_world.paths import MODS_DIR


def discover_mod_files(mods_dir: Path | None = None) -> list[Path]:
    root = mods_dir or MODS_DIR
    if not root.exists():
        return []
    return sorted(p for p in root.glob("*.py") if p.name != "__init__.py")


def load_mod_module(path: Path):
    module_name = f"nyc_world_mods.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load mod {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_mods(registry: NPCRegistry | None = None, mods_dir: Path | None = None) -> NPCRegistry:
    registry = registry or NPCRegistry()
    for path in discover_mod_files(mods_dir):
        module = load_mod_module(path)
        register = getattr(module, "register", None)
        if callable(register):
            register(registry)
    merge_into_game_dialogue()
    return registry


def load_mods_into_city(city, *, interactables: list | None = None, mods_dir: Path | None = None) -> list[str]:
    registry = load_mods(mods_dir=mods_dir)
    return registry.apply_to_city(city, interactables=interactables)

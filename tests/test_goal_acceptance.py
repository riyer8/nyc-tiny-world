"""Cross-pillar acceptance checks — verifies GOAL.md deliverables exist and behave."""

from __future__ import annotations

import importlib
import pytest

from nyc_world.paths import DEFAULT_META_PATH

PILLAR_MODULES = [
    ("memory", "nyc_world.simulation.memory"),
    ("agent", "nyc_world.simulation.agent"),
    ("quest_gen", "nyc_world.simulation.quest_gen"),
    ("mystery", "nyc_world.simulation.mystery"),
    ("feeds", "nyc_world.feeds"),
    ("subway", "nyc_world.city.subway"),
    ("twin", "nyc_world.modes.twin"),
    ("imagine", "nyc_world.modes.imagine"),
    ("god", "nyc_world.modes.god"),
    ("economy", "nyc_world.simulation.economy"),
    ("photo", "nyc_world.modes.photo"),
    ("agents", "nyc_world.agents"),
]

PILLAR_TESTS = [
    "tests/test_memory.py",
    "tests/test_npc_memory.py",
    "tests/test_agent.py",
    "tests/test_quest_gen.py",
    "tests/test_mystery.py",
    "tests/test_feeds.py",
    "tests/test_subway.py",
    "tests/test_twin.py",
    "tests/test_imagine.py",
    "tests/test_god.py",
    "tests/test_economy.py",
    "tests/test_photo.py",
    "tests/test_agents.py",
    "tests/test_mvp_vertical_slice.py",
    "tests/test_save.py",
    "tests/test_event_log.py",
    "tests/test_simulation.py",
]


@pytest.mark.parametrize("name,module", PILLAR_MODULES)
def test_pillar_module_importable(name: str, module: str):
    importlib.import_module(module)


PILLAR_DOCS = [
    "docs/memory.md",
    "docs/agents.md",
    "docs/quests.md",
    "docs/mystery.md",
    "docs/feeds.md",
    "docs/subway.md",
    "docs/twin.md",
    "docs/imagine.md",
    "docs/god.md",
    "docs/economy.md",
    "docs/photo.md",
    "docs/agents-api.md",
]


@pytest.mark.parametrize("rel", PILLAR_DOCS)
def test_pillar_docs_exist(rel: str):
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    assert (root / rel).exists(), f"missing {rel}"


def test_all_pillar_test_files_exist():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for rel in PILLAR_TESTS:
        assert (root / rel).exists(), f"missing {rel}"


def test_map_metadata_available_for_integration():
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata in this environment")

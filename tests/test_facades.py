"""Tests for facade texture lookup and building keys."""

from __future__ import annotations

import json
from pathlib import Path

from nyc_world.map.buildings import Building3D, facade_key_from_tags
from nyc_world.render.facades import FacadeCache, best_wall_index, reset_facade_cache


def test_facade_key_from_wikidata() -> None:
    key, wd = facade_key_from_tags({"wikidata": "Q3051566", "name": "Bobst Library"})
    assert key == "Q3051566"
    assert wd == "Q3051566"


def test_facade_key_from_name() -> None:
    key, wd = facade_key_from_tags({"name": "Jefferson Market Library"})
    assert key == "jefferson_market_library"
    assert wd == ""


def test_best_wall_faces_player() -> None:
    fp = ((0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0))
    # Player south of building — south wall (z=0) should face them.
    assert best_wall_index(fp, 5.0, -5.0) == 0


def test_facade_cache_manifest(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text(json.dumps({"Q123": "Q123.jpg"}))
    # Tiny valid JPEG header is enough for manifest lookup tests.
    (tmp_path / "Q123.jpg").write_bytes(
        b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        b"\xff\xd9"
    )

    reset_facade_cache()
    cache = FacadeCache(tmp_path)
    assert cache.has("Q123")
    assert not cache.has("Q999")


def test_shipped_facade_images_match_manifest() -> None:
    from nyc_world.paths import FACADES_DIR

    reset_facade_cache()
    cache = FacadeCache(FACADES_DIR)
    assert len(cache.manifest) >= 10
    missing = [key for key in cache.manifest if not cache.has(key)]
    assert missing == []


def test_building_carries_facade_key() -> None:
    building = Building3D(
        footprint=((0, 0), (10, 0), (10, 10), (0, 10)),
        height=12,
        wall_r=0.5,
        wall_g=0.5,
        wall_b=0.5,
        roof_r=0.4,
        roof_g=0.4,
        roof_b=0.4,
        facade_key="Q3051566",
        wikidata="Q3051566",
        name="Bobst Library",
    )
    assert building.facade_key == "Q3051566"

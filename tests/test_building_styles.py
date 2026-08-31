"""Tests for OSM-driven building appearance."""

from __future__ import annotations

from nyc_world.map.building_styles import style_from_tags
from nyc_world.map.buildings import Building3D


def test_brownstone_style():
    style = style_from_tags({"building": "terrace", "building:material": "brick"}, height_m=15)
    assert style.has_cornice
    assert style.wall[0] > 0.4  # warm brick tone


def test_office_glass_style():
    style = style_from_tags({"building": "office"}, height_m=80)
    assert style.material == "glass"
    assert style.window[2] > style.wall[2]


def test_building3d_from_style():
    style = style_from_tags({"building": "retail", "shop": "yes"}, height_m=8)
    b = Building3D.from_style(((0, 0), (10, 0), (10, 10), (0, 10)), 8, style)
    assert b.has_storefront
    assert b.levels >= 2

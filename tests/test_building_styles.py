"""Tests for OSM-driven building appearance."""

from __future__ import annotations

from nyc_world.map.building_styles import NYC_PALETTES, style_from_tags
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


def test_palette_has_nyc_range():
    assert len(NYC_PALETTES) >= 10
    walls = {name: palette.wall for name, palette in NYC_PALETTES.items()}
    assert walls["red_brick"][0] > walls["red_brick"][2]
    assert walls["limestone"][0] > 0.75
    assert walls["white_paint"][0] > 0.85
    assert walls["dark_glass"][2] > walls["dark_glass"][0]


def test_colour_tag_overrides_wall():
    style = style_from_tags(
        {"building": "yes", "building:colour": "white"},
        height_m=18,
        variety_seed="a",
    )
    assert style.wall[0] >= 0.85


def test_untagged_neighbors_vary():
    a = style_from_tags({"building": "apartments"}, height_m=16, variety_seed="10.0,20.0")
    b = style_from_tags({"building": "apartments"}, height_m=16, variety_seed="40.0,80.0")
    c = style_from_tags({"building": "yes"}, height_m=10, variety_seed="1.0,2.0")
    walls = {a.wall, b.wall, c.wall}
    assert len(walls) >= 2


def test_prewar_stone_from_year():
    style = style_from_tags(
        {"building": "yes", "start_date": "1912"},
        height_m=30,
        variety_seed="prewar",
    )
    assert style.has_cornice
    assert style.material in ("stone", "brick")


def test_wood_material_is_brown():
    style = style_from_tags(
        {"building": "yes", "building:material": "wood"},
        height_m=8,
        variety_seed="woodlot",
    )
    assert style.material == "wood"
    assert style.wall[0] > style.wall[2]
    assert style.wall[1] < 0.40


def test_storefront_only_for_retail_amenities():
    cafe = style_from_tags(
        {"building": "yes", "amenity": "cafe"},
        height_m=10,
        variety_seed="cafe",
    )
    dentist = style_from_tags(
        {"building": "apartments", "amenity": "dentist"},
        height_m=16,
        variety_seed="dentist",
    )
    assert cafe.has_storefront
    assert not dentist.has_storefront

"""Building appearance from OSM tags — materials, era, and NYC archetypes."""

from __future__ import annotations

import re
from dataclasses import dataclass


RGB = tuple[float, float, float]


@dataclass(frozen=True)
class BuildingStyle:
    building_type: str
    material: str
    levels: int
    roof_style: str  # flat, pitched, parapet
    wall: RGB
    roof: RGB
    trim: RGB
    window: RGB
    has_storefront: bool = False
    has_cornice: bool = False


@dataclass(frozen=True)
class _Palette:
    wall: RGB
    roof: RGB
    trim: RGB
    window: RGB
    material: str


# Sampled from West Village / SoHo / NYU facades — not a height-only gray ramp.
NYC_PALETTES: dict[str, _Palette] = {
    "brownstone": _Palette((0.55, 0.33, 0.25), (0.40, 0.28, 0.22), (0.90, 0.86, 0.80), (0.20, 0.26, 0.36), "brick"),
    "red_brick": _Palette((0.62, 0.28, 0.22), (0.42, 0.26, 0.20), (0.88, 0.84, 0.78), (0.18, 0.24, 0.32), "brick"),
    "yellow_brick": _Palette((0.76, 0.64, 0.42), (0.48, 0.40, 0.30), (0.86, 0.82, 0.74), (0.22, 0.28, 0.36), "brick"),
    "buff_brick": _Palette((0.70, 0.56, 0.40), (0.46, 0.36, 0.28), (0.84, 0.80, 0.72), (0.20, 0.26, 0.34), "brick"),
    "dark_brick": _Palette((0.38, 0.24, 0.18), (0.28, 0.20, 0.16), (0.82, 0.78, 0.72), (0.16, 0.20, 0.28), "brick"),
    "limestone": _Palette((0.82, 0.78, 0.66), (0.55, 0.50, 0.42), (0.92, 0.90, 0.84), (0.24, 0.30, 0.38), "stone"),
    "white_paint": _Palette((0.90, 0.88, 0.84), (0.62, 0.58, 0.52), (0.78, 0.76, 0.72), (0.28, 0.34, 0.42), "brick"),
    "terra_cotta": _Palette((0.72, 0.42, 0.30), (0.48, 0.32, 0.24), (0.88, 0.82, 0.74), (0.20, 0.26, 0.34), "brick"),
    "granite": _Palette((0.50, 0.50, 0.52), (0.38, 0.38, 0.40), (0.78, 0.78, 0.80), (0.22, 0.28, 0.36), "stone"),
    "cast_iron": _Palette((0.32, 0.30, 0.28), (0.24, 0.22, 0.20), (0.70, 0.68, 0.64), (0.35, 0.42, 0.50), "metal"),
    "wood": _Palette((0.48, 0.32, 0.20), (0.32, 0.22, 0.14), (0.72, 0.58, 0.42), (0.22, 0.28, 0.34), "wood"),
    "glass_blue": _Palette((0.40, 0.48, 0.58), (0.30, 0.36, 0.44), (0.55, 0.60, 0.66), (0.55, 0.70, 0.84), "glass"),
    "dark_glass": _Palette((0.22, 0.26, 0.34), (0.16, 0.18, 0.24), (0.48, 0.52, 0.58), (0.40, 0.55, 0.70), "glass"),
}

# Street-level retail glass — not every OSM amenity (dentist, school, …).
_STOREFRONT_AMENITIES = {
    "bank",
    "bar",
    "biergarten",
    "cafe",
    "fast_food",
    "food_court",
    "ice_cream",
    "marketplace",
    "nightclub",
    "pharmacy",
    "pub",
    "restaurant",
}

_RESIDENTIAL_LOW = ("brownstone", "red_brick", "yellow_brick", "white_paint", "buff_brick", "dark_brick")
_RESIDENTIAL_MID = ("red_brick", "buff_brick", "limestone", "yellow_brick", "terra_cotta", "white_paint")
_UNIVERSITY = ("red_brick", "limestone", "yellow_brick", "glass_blue", "buff_brick", "white_paint")
_TOWER = ("glass_blue", "dark_glass", "limestone", "granite")
_INDUSTRIAL = ("cast_iron", "buff_brick", "dark_brick", "granite")
_CIVIC = ("limestone", "red_brick", "granite", "yellow_brick")
_PREWAR = ("limestone", "brownstone", "terra_cotta", "red_brick")


def _parse_color(tag: str) -> RGB | None:
    tag = tag.strip().lower()
    named = {
        "red": (0.65, 0.22, 0.18),
        "brown": (0.45, 0.32, 0.24),
        "grey": (0.55, 0.56, 0.58),
        "gray": (0.55, 0.56, 0.58),
        "white": (0.88, 0.88, 0.90),
        "yellow": (0.82, 0.72, 0.45),
        "blue": (0.35, 0.45, 0.62),
        "green": (0.35, 0.50, 0.38),
        "black": (0.18, 0.18, 0.20),
        "brick": (0.58, 0.34, 0.26),
        "cream": (0.90, 0.84, 0.70),
        "beige": (0.82, 0.74, 0.60),
        "tan": (0.72, 0.58, 0.42),
        "ivory": (0.92, 0.88, 0.78),
        "sandstone": (0.78, 0.64, 0.46),
        "terracotta": (0.72, 0.42, 0.30),
    }
    if tag in named:
        return named[tag]
    if tag.startswith("#") and len(tag) in (4, 7):
        try:
            if len(tag) == 4:
                r = int(tag[1] * 2, 16) / 255
                g = int(tag[2] * 2, 16) / 255
                b = int(tag[3] * 2, 16) / 255
            else:
                r = int(tag[1:3], 16) / 255
                g = int(tag[3:5], 16) / 255
                b = int(tag[5:7], 16) / 255
            return (r, g, b)
        except ValueError:
            return None
    return None


def _parse_levels(tags: dict) -> int:
    for key in ("building:levels", "levels"):
        if key in tags:
            raw = tags[key].split(";")[0].split(",")[0]
            try:
                return max(1, int(float(raw)))
            except ValueError:
                pass
    return 0


def _parse_year(tags: dict) -> int | None:
    for key in ("start_date", "building:year_built", "year_of_construction"):
        if key in tags:
            m = re.search(r"\d{4}", tags[key])
            if m:
                return int(m.group())
    return None


def _stable_index(seed: str, modulo: int) -> int:
    h = 2166136261
    for ch in seed:
        h ^= ord(ch)
        h = (h * 16777619) & 0xFFFFFFFF
    return h % modulo


def _choice(seed: str, names: tuple[str, ...]) -> str:
    return names[_stable_index(seed, len(names))]


def variety_seed_from_tags(tags: dict, extra: str = "") -> str:
    """Stable seed so untagged neighbors still get different facades."""
    return "|".join(
        (
            extra,
            tags.get("name", ""),
            tags.get("wikidata", ""),
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("building", ""),
        )
    )


def _palette_name(
    tags: dict,
    *,
    height_m: float,
    material: str,
    btype: str,
    year: int | None,
    seed: str,
) -> str:
    material = material.lower()

    if material in ("glass", "metal", "steel", "curtain_wall"):
        return "dark_glass" if height_m > 60 else "glass_blue"
    if material == "brick":
        return _choice(seed, ("red_brick", "yellow_brick", "buff_brick", "dark_brick", "brownstone"))
    if material in ("stone", "limestone", "sandstone"):
        return "limestone"
    if material == "marble":
        return "white_paint"
    if material in ("concrete", "cement"):
        return _choice(seed, ("granite", "limestone", "white_paint"))
    if material == "wood":
        return "wood"
    if material in ("cast_iron", "iron"):
        return "cast_iron"

    if btype in ("terrace", "row_house", "brownstone"):
        return _choice(seed, ("brownstone", "red_brick", "dark_brick"))
    if btype in ("house", "detached", "semidetached_house"):
        return _choice(seed, ("white_paint", "red_brick", "brownstone", "yellow_brick"))
    if btype in ("church", "cathedral", "chapel"):
        return _choice(seed, _CIVIC)
    if btype == "school":
        return _choice(seed, ("yellow_brick", "red_brick", "limestone"))
    if btype in ("university", "college", "dormitory"):
        if height_m > 45:
            return _choice(seed, ("glass_blue", "red_brick", "limestone"))
        return _choice(seed, _UNIVERSITY)
    if btype in ("office", "commercial", "hotel"):
        return "dark_glass" if height_m > 60 else "glass_blue"
    if height_m > 45:
        return _choice(seed, _TOWER)
    if btype in ("industrial", "warehouse", "garage"):
        return _choice(seed, _INDUSTRIAL)

    if year and year < 1940:
        return _choice(seed, _PREWAR)
    if year and year >= 1980 and height_m > 30:
        return _choice(seed, _TOWER)

    if height_m < 22:
        return _choice(seed, _RESIDENTIAL_LOW)
    if height_m < 45:
        return _choice(seed, _RESIDENTIAL_MID)
    return _choice(seed, _TOWER)


def _roof_style(btype: str, height_m: float, palette_name: str) -> str:
    if palette_name in ("glass_blue", "dark_glass"):
        return "flat"
    if btype in ("house", "detached", "church") and height_m < 18:
        return "pitched"
    if height_m < 45:
        return "parapet"
    return "flat"


def style_from_tags(
    tags: dict,
    *,
    height_m: float,
    variety_seed: str = "",
) -> BuildingStyle:
    """Derive facade colors and features from OpenStreetMap building tags."""
    btype = tags.get("building", "yes")
    material = tags.get("building:material") or tags.get("facade:material") or tags.get("material", "")
    levels = _parse_levels(tags)
    year = _parse_year(tags)
    seed = variety_seed_from_tags(tags, variety_seed)

    colour = None
    for key in ("building:colour", "colour", "facade:colour"):
        if key in tags:
            colour = _parse_color(tags[key])
            if colour:
                break

    name = _palette_name(
        tags, height_m=height_m, material=material, btype=btype, year=year, seed=seed
    )
    palette = NYC_PALETTES[name]
    wall = colour or palette.wall
    masonry = name not in ("glass_blue", "dark_glass")
    amenity = (tags.get("amenity") or "").split(";")[0].strip().lower()
    storefront = (
        "shop" in tags
        or amenity in _STOREFRONT_AMENITIES
        or btype in ("retail", "commercial", "store")
    )
    cornice = masonry and (
        btype in ("terrace", "row_house", "brownstone")
        or (year is not None and year < 1940)
        or (12 <= height_m <= 50)
    )

    return BuildingStyle(
        btype,
        material or palette.material,
        levels or max(2, int(height_m / 3.5)),
        _roof_style(btype, height_m, name),
        wall,
        palette.roof,
        palette.trim,
        palette.window,
        has_storefront=storefront,
        has_cornice=cornice,
    )

"""Building appearance from OSM tags — materials, era, and NYC archetypes."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class BuildingStyle:
    building_type: str
    material: str
    levels: int
    roof_style: str  # flat, pitched, parapet
    wall: tuple[float, float, float]
    roof: tuple[float, float, float]
    trim: tuple[float, float, float]
    window: tuple[float, float, float]
    has_storefront: bool = False
    has_cornice: bool = False


def _parse_color(tag: str) -> tuple[float, float, float] | None:
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


def style_from_tags(tags: dict, *, height_m: float) -> BuildingStyle:
    """Derive facade colors and features from OpenStreetMap building tags."""
    btype = tags.get("building", "yes")
    material = tags.get("building:material") or tags.get("facade:material") or tags.get("material", "")
    levels = _parse_levels(tags)
    year = _parse_year(tags)

    colour = None
    for key in ("building:colour", "colour", "facade:colour"):
        if key in tags:
            colour = _parse_color(tags[key])
            if colour:
                break

    # NYC brownstone / row house
    if btype in ("terrace", "row_house", "brownstone") or (height_m < 22 and btype in ("apartments", "residential", "house")):
        wall = colour or (0.52, 0.36, 0.28)
        return BuildingStyle(
            btype, material or "brick", levels or max(2, int(height_m / 3.5)),
            "parapet", wall, (0.42, 0.30, 0.24), (0.90, 0.88, 0.84), (0.22, 0.28, 0.38),
            has_storefront=tags.get("shop") is not None or btype == "retail",
            has_cornice=True,
        )

    # Brick walk-up
    if material in ("brick", "stone") or btype in ("house", "detached", "church", "school"):
        wall = colour or (0.58, 0.40, 0.30) if material == "brick" else (0.62, 0.62, 0.66)
        return BuildingStyle(
            btype, material or "brick", levels or max(2, int(height_m / 3.5)),
            "pitched" if height_m < 18 else "parapet",
            wall, (0.48, 0.34, 0.26), (0.85, 0.85, 0.88), (0.18, 0.24, 0.32),
            has_storefront="shop" in tags or "amenity" in tags,
        )

    # Glass office tower
    if btype in ("office", "commercial", "hotel") or height_m > 45:
        wall = colour or (0.38, 0.42, 0.50)
        return BuildingStyle(
            btype, material or "glass", levels or max(4, int(height_m / 3.5)),
            "flat", wall, (0.32, 0.36, 0.44), (0.55, 0.58, 0.62), (0.55, 0.68, 0.82),
            has_cornice=height_m > 60,
        )

    # Pre-war vs modern from year
    if year and year < 1940:
        wall = colour or (0.56, 0.54, 0.52)
        return BuildingStyle(
            btype, material or "stone", levels or max(3, int(height_m / 3.5)),
            "parapet", wall, (0.48, 0.46, 0.44), (0.88, 0.86, 0.82), (0.20, 0.26, 0.34),
            has_storefront=True, has_cornice=True,
        )

    # Default mid-rise
    if height_m < 12:
        wall = colour or (0.60, 0.61, 0.64)
        roof = (0.66, 0.67, 0.70)
    elif height_m < 45:
        wall = colour or (0.42, 0.46, 0.54)
        roof = (0.50, 0.54, 0.60)
    else:
        wall = colour or (0.28, 0.34, 0.48)
        roof = (0.36, 0.42, 0.54)

    return BuildingStyle(
        btype, material, levels or max(2, int(height_m / 3.5)),
        "flat", wall, roof, (0.75, 0.76, 0.78), (0.22, 0.28, 0.36),
        has_storefront=btype in ("retail", "commercial", "store"),
    )

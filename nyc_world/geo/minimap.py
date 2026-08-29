"""Hierarchical NYC mini-map rendering — high-res with visible borough maps."""

from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from nyc_world.core.projection import GeoProjection
from nyc_world.core.sprites import BUILDING, PARK, ROAD, SIDEWALK, TREE
from nyc_world.core.world import World
from nyc_world.geo.coords import world_xz_to_gps
from nyc_world.geo.regions import MANHATTAN, NYC, GeoRegion

if False:  # TYPE_CHECKING without import cycle
    from nyc_world.streaming.state import StreamingState

MINIMAP_SCALE = 2  # internal 2× resolution for crisp output

TILE_COLORS = {
    SIDEWALK: (205, 200, 190),
    BUILDING: (118, 116, 128),
    ROAD: (72, 72, 78),
    PARK: (88, 148, 82),
    TREE: (68, 128, 68),
    "O": (178, 138, 88),
    "P": (78, 158, 218),
}

# Borough land polygons as (lat, lon) — simplified silhouettes for the NYC overview.
BOROUGH_LAND: dict[str, list[tuple[float, float]]] = {
    "Manhattan": [
        (40.705, -74.018), (40.708, -73.930), (40.795, -73.925),
        (40.880, -73.910), (40.878, -74.015), (40.820, -74.020),
        (40.750, -74.018), (40.705, -74.018),
    ],
    "Brooklyn": [
        (40.570, -74.040), (40.590, -73.830), (40.700, -73.835),
        (40.705, -74.020), (40.650, -74.040), (40.570, -74.040),
    ],
    "Queens": [
        (40.570, -73.820), (40.590, -73.700), (40.800, -73.720),
        (40.820, -73.880), (40.700, -73.835), (40.570, -73.820),
    ],
    "Bronx": [
        (40.800, -73.930), (40.820, -73.765), (40.915, -73.765),
        (40.900, -73.930), (40.800, -73.930),
    ],
    "Staten Island": [
        (40.500, -74.260), (40.520, -74.130), (40.640, -74.100),
        (40.650, -74.220), (40.500, -74.260),
    ],
}

BOROUGH_COLORS: dict[str, tuple[int, int, int]] = {
    "Manhattan": (145, 155, 175),
    "Brooklyn": (130, 140, 125),
    "Queens": (125, 135, 145),
    "Bronx": (135, 130, 120),
    "Staten Island": (120, 130, 115),
}

WATER = (28, 45, 72)
LAND_BG = (38, 52, 68)


@dataclass
class MinimapState:
    surface: pygame.Surface
    width: int
    height: int


def _font(size: int, bold: bool = False):
    return pygame.font.SysFont(
        "sf pro display,helvetica neue,menlo,monaco,arial",
        size * MINIMAP_SCALE,
        bold=bold,
    )


def _scale_down(surf: pygame.Surface) -> pygame.Surface:
    w, h = surf.get_size()
    return pygame.transform.smoothscale(surf, (w // MINIMAP_SCALE, h // MINIMAP_SCALE))


def _latlon_poly(region: GeoRegion, points: list[tuple[float, float]], inner: pygame.Rect) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for lat, lon in points:
        nx, ny = region.normalize(lat, lon)
        out.append((inner.x + int(nx * inner.width), inner.y + int((1 - ny) * inner.height)))
    return out


def _draw_water_and_boroughs(surf: pygame.Surface, inner: pygame.Rect, region: GeoRegion) -> None:
    pygame.draw.rect(surf, WATER, inner)
    for name, points in BOROUGH_LAND.items():
        poly = _latlon_poly(region, points, inner)
        if len(poly) >= 3:
            color = BOROUGH_COLORS.get(name, LAND_BG)
            pygame.draw.polygon(surf, color, poly)
            pygame.draw.polygon(surf, (color[0] + 20, color[1] + 20, color[2] + 20), poly, 1)


def _draw_highlight_box(
    surf: pygame.Surface,
    inner: pygame.Rect,
    region: GeoRegion,
    highlight: GeoRegion,
    color: tuple[int, int, int],
    width: int = 2,
) -> None:
    hx0, hy0 = highlight.normalize(highlight.south, highlight.west)
    hx1, hy1 = highlight.normalize(highlight.north, highlight.east)
    # Ensure min visible size (playable area is tiny on NYC scale)
    bw = max(6, int((hx1 - hx0) * inner.width))
    bh = max(6, int((hy1 - hy0) * inner.height))
    box = pygame.Rect(
        inner.x + int(hx0 * inner.width),
        inner.y + int((1 - hy1) * inner.height),
        bw,
        bh,
    )
    pygame.draw.rect(surf, color, box, width)


def _draw_player_dot(
    surf: pygame.Surface,
    inner: pygame.Rect,
    region: GeoRegion,
    lat: float,
    lon: float,
    *,
    radius: int = 5,
) -> None:
    px, py = region.normalize(lat, lon)
    dot_x = inner.x + int(px * inner.width)
    dot_y = inner.y + int((1 - py) * inner.height)
    # Glow
    pygame.draw.circle(surf, (50, 120, 220), (dot_x, dot_y), radius + 3)
    pygame.draw.circle(surf, (70, 150, 255), (dot_x, dot_y), radius)
    pygame.draw.circle(surf, (240, 248, 255), (dot_x, dot_y), max(2, radius - 2))


def _draw_north(surf: pygame.Surface, rect: pygame.Rect) -> None:
    f = _font(9)
    nx = rect.right - 14 * MINIMAP_SCALE
    ny = rect.y + 6 * MINIMAP_SCALE
    pygame.draw.polygon(
        surf,
        (240, 190, 70),
        [(nx, ny), (nx - 5 * MINIMAP_SCALE, ny + 10 * MINIMAP_SCALE), (nx + 5 * MINIMAP_SCALE, ny + 10 * MINIMAP_SCALE)],
    )
    surf.blit(f.render("N", True, (240, 190, 70)), (nx - 5 * MINIMAP_SCALE, ny + 8 * MINIMAP_SCALE))


def _draw_radius_circle(
    surf: pygame.Surface,
    inner: pygame.Rect,
    region: GeoRegion,
    center_lat: float,
    center_lon: float,
    radius_m: float,
    color: tuple[int, int, int],
) -> None:
    from nyc_world.streaming.tiles import METERS_PER_DEGREE_LAT, meters_per_degree_lon

    cx, cy = region.normalize(center_lat, center_lon)
    center_x = inner.x + int(cx * inner.width)
    center_y = inner.y + int((1 - cy) * inner.height)
    m_per_deg_lon = meters_per_degree_lon(center_lat)
    radius_lat = radius_m / METERS_PER_DEGREE_LAT
    radius_lon = radius_m / m_per_deg_lon
    px, _ = region.normalize(center_lat + radius_lat, center_lon)
    _, qy = region.normalize(center_lat, center_lon + radius_lon)
    rx = abs(int((px - cx) * inner.width))
    ry = abs(int((qy - cy) * inner.height))
    radius_px = max(rx, ry, 4 * MINIMAP_SCALE)
    pygame.draw.circle(surf, color, (center_x, center_y), radius_px, max(1, MINIMAP_SCALE))


def _draw_region_frame(
    surf: pygame.Surface,
    rect: pygame.Rect,
    region: GeoRegion,
    player_lat: float,
    player_lon: float,
    *,
    highlight: GeoRegion | None = None,
    title: str | None = None,
    streaming: "StreamingState | None" = None,
    draw_boroughs: bool = False,
    street_grid: bool = False,
) -> None:
    title_font = _font(11, bold=True)
    pygame.draw.rect(surf, (18, 22, 32), rect, border_radius=6 * MINIMAP_SCALE)
    pygame.draw.rect(surf, (60, 75, 100), rect, max(1, MINIMAP_SCALE), border_radius=6 * MINIMAP_SCALE)
    label = title or region.name
    surf.blit(title_font.render(label, True, (200, 210, 225)), (rect.x + 8 * MINIMAP_SCALE, rect.y + 5 * MINIMAP_SCALE))

    inner = rect.inflate(-14 * MINIMAP_SCALE, -24 * MINIMAP_SCALE)

    if draw_boroughs:
        _draw_water_and_boroughs(surf, inner, region)
    else:
        pygame.draw.rect(surf, WATER, inner)
        # Manhattan island shape on the Manhattan panel
        manhattan_poly = _latlon_poly(region, BOROUGH_LAND["Manhattan"], inner)
        if len(manhattan_poly) >= 3:
            pygame.draw.polygon(surf, (130, 140, 155), manhattan_poly)
            pygame.draw.polygon(surf, (160, 170, 185), manhattan_poly, max(1, MINIMAP_SCALE))

    if street_grid and region.name == "Manhattan":
        for i in range(1, 12):
            t = i / 12
            x = inner.x + int(t * inner.width)
            pygame.draw.line(surf, (90, 100, 115), (x, inner.y), (x, inner.bottom), 1)
        for i in range(1, 20):
            t = i / 20
            y = inner.y + int(t * inner.height)
            pygame.draw.line(surf, (90, 100, 115), (inner.x, y), (inner.right, y), 1)
        # Central Park
        cp_lat, cp_lon = 40.782, -73.965
        cpx, cpy = region.normalize(cp_lat, cp_lon)
        cpw = max(8, int(0.04 * inner.width))
        cph = max(20, int(0.22 * inner.height))
        park = pygame.Rect(
            inner.x + int(cpx * inner.width) - cpw // 2,
            inner.y + int((1 - cpy) * inner.height) - cph // 2,
            cpw,
            cph,
        )
        pygame.draw.rect(surf, (72, 130, 78), park)

    if highlight:
        _draw_highlight_box(surf, inner, region, highlight, (255, 210, 80), width=max(2, MINIMAP_SCALE))

    if streaming and region.name == "Manhattan":
        _draw_radius_circle(surf, inner, region, player_lat, player_lon, streaming.data_radius_m, (50, 100, 180))
        _draw_radius_circle(surf, inner, region, player_lat, player_lon, streaming.render_radius_m, (100, 180, 255))

    _draw_player_dot(surf, inner, region, player_lat, player_lon)
    _draw_north(surf, rect)


def _draw_neighborhood_map(
    surf: pygame.Surface,
    rect: pygame.Rect,
    world: World,
    player_x: float,
    player_z: float,
    world_width_m: float,
    world_depth_m: float,
    yaw: float,
    title: str,
) -> None:
    title_font = _font(11, bold=True)
    pygame.draw.rect(surf, (18, 22, 32), rect, border_radius=6 * MINIMAP_SCALE)
    pygame.draw.rect(surf, (60, 75, 100), rect, max(1, MINIMAP_SCALE), border_radius=6 * MINIMAP_SCALE)
    surf.blit(title_font.render(title, True, (200, 210, 225)), (rect.x + 8 * MINIMAP_SCALE, rect.y + 5 * MINIMAP_SCALE))

    inner = rect.inflate(-14 * MINIMAP_SCALE, -24 * MINIMAP_SCALE)
    map_surf = pygame.Surface((inner.width, inner.height))
    map_surf.fill((42, 44, 54))

    cols, rows = world.cols, world.rows
    for row in range(rows):
        for col in range(cols):
            tile = world.tile_at(col, row)
            color = TILE_COLORS.get(tile, TILE_COLORS[SIDEWALK])
            mx = int(col / cols * inner.width)
            my = int(row / rows * inner.height)
            mw = max(1, int((col + 1) / cols * inner.width) - mx)
            mh = max(1, int((row + 1) / rows * inner.height) - my)
            pygame.draw.rect(map_surf, color, (mx, my, mw, mh))

    frac_x = max(0.0, min(1.0, player_x / world_width_m))
    frac_z = max(0.0, min(1.0, player_z / world_depth_m))
    dot_x = int(frac_x * (inner.width - 1))
    dot_y = int((1.0 - frac_z) * (inner.height - 1))

    arrow_len = 14 * MINIMAP_SCALE
    ax = math.sin(yaw) * arrow_len
    ay = -math.cos(yaw) * arrow_len
    pygame.draw.line(
        map_surf,
        (255, 220, 100),
        (dot_x, dot_y),
        (int(dot_x + ax), int(dot_y + ay)),
        max(2, MINIMAP_SCALE),
    )
    pygame.draw.circle(map_surf, (50, 120, 220), (dot_x, dot_y), 6 * MINIMAP_SCALE)
    pygame.draw.circle(map_surf, (70, 150, 255), (dot_x, dot_y), 4 * MINIMAP_SCALE)
    pygame.draw.circle(map_surf, (240, 248, 255), (dot_x, dot_y), 2 * MINIMAP_SCALE)

    surf.blit(map_surf, inner.topleft)
    _draw_north(surf, rect)


def build_minimap(
    world: World,
    projection: GeoProjection,
    meters_per_tile: float,
    player_x: float,
    player_z: float,
    yaw: float,
    world_width_m: float,
    world_depth_m: float,
    streaming: "StreamingState | None" = None,
) -> MinimapState:
    """Build hierarchical mini-map — NYC, Manhattan, and neighborhood."""
    lat, lon = world_xz_to_gps(player_x, player_z, projection, meters_per_tile)

    # Internal 2× canvas → smooth downscale for crisp HUD
    width, height = 260 * MINIMAP_SCALE, 300 * MINIMAP_SCALE
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))

    pad = 10 * MINIMAP_SCALE
    city_h = 92 * MINIMAP_SCALE
    borough_h = 82 * MINIMAP_SCALE
    hood_h = height - city_h - borough_h - pad * 4

    city_rect = pygame.Rect(pad, pad, width - pad * 2, city_h)
    borough_rect = pygame.Rect(pad, city_rect.bottom + pad, width - pad * 2, borough_h)
    hood_rect = pygame.Rect(pad, borough_rect.bottom + pad, width - pad * 2, hood_h)

    playable = GeoRegion(
        projection.area_name,
        projection.south,
        projection.west,
        projection.north,
        projection.east,
    )

    _draw_region_frame(
        surf, city_rect, NYC, lat, lon,
        highlight=MANHATTAN,
        title="🗽 NYC",
        draw_boroughs=True,
    )
    _draw_region_frame(
        surf, borough_rect, MANHATTAN, lat, lon,
        highlight=playable,
        title="Manhattan",
        streaming=streaming,
        street_grid=True,
    )
    _draw_neighborhood_map(
        surf, hood_rect, world, player_x, player_z,
        world_width_m, world_depth_m, yaw, projection.area_name,
    )

    if streaming:
        legend = _font(9)
        surf.blit(
            legend.render(
                f"○ {streaming.data_radius_m / 1609:.1f} mi data  ·  {len(streaming.loaded_tile_ids)} tiles",
                True,
                (130, 165, 210),
            ),
            (pad, height - 12 * MINIMAP_SCALE),
        )

    scaled = _scale_down(surf)
    return MinimapState(surface=scaled, width=scaled.get_width(), height=scaled.get_height())

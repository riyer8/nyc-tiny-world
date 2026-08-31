"""Procedural meshes — detailed buildings, vehicles, and pedestrians."""

from __future__ import annotations

import math

from nyc_world.city.npcs import NPC
from nyc_world.city.vehicles import BIKE, BUS, CAR, TAXI, Vehicle
from nyc_world.core.world_3d import Box3D
from nyc_world.map.buildings import Building3D

# Sun direction for simple directional shading (fixed afternoon sun).
_SUN_X, _SUN_Z = 0.55, 0.45


def _shade(rgb: tuple[float, float, float], factor: float) -> tuple[float, float, float]:
    return tuple(max(0.0, min(1.0, c * factor)) for c in rgb)


def _wall_shade(nx: float, nz: float) -> float:
    dot = max(0.0, nx * _SUN_X + nz * _SUN_Z)
    return 0.62 + 0.38 * dot


def _draw_box(box: Box3D) -> None:
    from nyc_world.render.render_gl import draw_box

    draw_box(box)


def _draw_quad_y(
    x0: float, y0: float, z0: float,
    x1: float, y1: float, z1: float,
    x2: float, y2: float, z2: float,
    x3: float, y3: float, z3: float,
    r: float, g: float, b: float,
) -> None:
    from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

    glColor3f(r, g, b)
    glBegin(GL_QUADS)
    glVertex3f(x0, y0, z0)
    glVertex3f(x1, y1, z1)
    glVertex3f(x2, y2, z2)
    glVertex3f(x3, y3, z3)
    glEnd()


# Distance-based building detail (meters from player).
DETAIL_FULL_M = 65.0
DETAIL_MEDIUM_M = 130.0
MAX_WINDOW_STORIES = 5
MAX_WINDOW_COLS = 3
SKIP_WINDOWS_BELOW_M = 12.0


def _building_dist_sq(building: Building3D, px: float, pz: float) -> float:
    xs = [p[0] for p in building.footprint]
    zs = [p[1] for p in building.footprint]
    cx = sum(xs) / len(xs)
    cz = sum(zs) / len(zs)
    dx, dz = cx - px, cz - pz
    return dx * dx + dz * dz


def draw_building_detailed(
    building: Building3D,
    brightness: float = 1.0,
    *,
    detail: str = "full",
) -> None:
    """Extruded footprint — detail: full | medium | simple."""
    if detail == "simple":
        from nyc_world.render.render_gl import _draw_building_simple

        _draw_building_simple(building, brightness)
        return

    fp = building.footprint
    if len(fp) < 3:
        return

    h = building.height
    wall = (building.wall_r, building.wall_g, building.wall_b)
    roof = (building.roof_r, building.roof_g, building.roof_b)
    trim = (building.trim_r, building.trim_g, building.trim_b)
    window = (building.window_r, building.window_g, building.window_b)
    story_h = 3.2
    draw_windows = detail == "full" and h >= SKIP_WINDOWS_BELOW_M

    for i in range(len(fp)):
        x0, z0 = fp[i]
        x1, z1 = fp[(i + 1) % len(fp)]
        dx, dz = x1 - x0, z1 - z0
        length = math.hypot(dx, dz)
        if length < 0.5:
            continue
        nx, nz = -dz / length, dx / length
        shade = _wall_shade(nx, nz) * brightness

        wr, wg, wb = _shade(wall, shade)
        _draw_quad_y(x0, 0, z0, x1, 0, z1, x1, h, z1, x0, h, z0, wr, wg, wb)

        if draw_windows:
            stories = min(building.levels or max(1, int(h / story_h)), MAX_WINDOW_STORIES)
            cols = min(max(1, int(length / 2.8)), MAX_WINDOW_COLS)
            for s in range(stories):
                y0 = s * story_h + 0.6
                y1 = min(h - 0.3, y0 + story_h * 0.55)
                if y1 <= y0:
                    continue
                for c in range(cols):
                    t0 = (c + 0.15) / cols
                    t1 = (c + 0.85) / cols
                    wx0 = x0 + dx * t0
                    wz0 = z0 + dz * t0
                    wx1 = x0 + dx * t1
                    wz1 = z0 + dz * t1
                    inset = 0.06
                    win_bright = (0.85 if (s + c) % 3 else 0.55) * brightness
                    wr2, wg2, wb2 = _shade(window, shade * win_bright)
                    _draw_quad_y(
                        wx0 + nx * inset, y0, wz0 + nz * inset,
                        wx1 + nx * inset, y0, wz1 + nz * inset,
                        wx1 + nx * inset, y1, wz1 + nz * inset,
                        wx0 + nx * inset, y1, wz0 + nz * inset,
                        wr2, wg2, wb2,
                    )
        elif detail == "medium" and h >= SKIP_WINDOWS_BELOW_M:
            # One band per floor — cheap but reads as windows at distance.
            stories = min(building.levels or max(1, int(h / story_h)), MAX_WINDOW_STORIES)
            for s in range(stories):
                y0 = s * story_h + 0.7
                y1 = min(h - 0.3, y0 + story_h * 0.4)
                wr2, wg2, wb2 = _shade(window, shade * 0.65 * brightness)
                _draw_quad_y(
                    x0 + nx * 0.05, y0, z0 + nz * 0.05,
                    x1 + nx * 0.05, y0, z1 + nz * 0.05,
                    x1 + nx * 0.05, y1, z1 + nz * 0.05,
                    x0 + nx * 0.05, y1, z0 + nz * 0.05,
                    wr2, wg2, wb2,
                )

        if building.has_storefront and h > 3 and detail == "full":
            sr, sg, sb = _shade(trim, shade * 1.1 * brightness)
            _draw_quad_y(
                x0 + nx * 0.04, 0.1, z0 + nz * 0.04,
                x1 + nx * 0.04, 0.1, z1 + nz * 0.04,
                x1 + nx * 0.04, min(3.2, h * 0.35), z1 + nz * 0.04,
                x0 + nx * 0.04, min(3.2, h * 0.35), z0 + nz * 0.04,
                sr, sg, sb,
            )

        if building.has_cornice and detail != "simple":
            cr, cg, cb = _shade(trim, shade * brightness)
            _draw_quad_y(x0, h - 0.35, z0, x1, h - 0.35, z1, x1, h, z1, x0, h, z0, cr, cg, cb)

    rr, rg, rb = _shade(roof, brightness)
    if building.roof_style == "pitched" and len(fp) >= 4 and detail == "full":
        cx = sum(p[0] for p in fp) / len(fp)
        cz = sum(p[1] for p in fp) / len(fp)
        peak = h + min(4.0, h * 0.2)
        for i in range(len(fp)):
            x0, z0 = fp[i]
            x1, z1 = fp[(i + 1) % len(fp)]
            _draw_quad_y(x0, h, z0, x1, h, z1, cx, peak, cz, cx, peak, cz, rr, rg, rb)
    else:
        from OpenGL.GL import GL_TRIANGLE_FAN, glBegin, glColor3f, glEnd, glVertex3f

        glColor3f(rr, rg, rb)
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(fp[0][0], h, fp[0][1])
        for x, z in fp[1:]:
            glVertex3f(x, h, z)
        glEnd()
        if building.roof_style == "parapet":
            for i in range(len(fp)):
                x0, z0 = fp[i]
                x1, z1 = fp[(i + 1) % len(fp)]
                tr, tg, tb = _shade(trim, brightness)
                _draw_quad_y(x0, h, z0, x1, h, z1, x1, h + 0.5, z1, x0, h + 0.5, z0, tr, tg, tb)


def _with_transform(x: float, z: float, heading: float, draw_fn) -> None:
    from OpenGL.GL import glPopMatrix, glPushMatrix, glRotatef, glTranslatef

    glPushMatrix()
    glTranslatef(x, 0, z)
    glRotatef(math.degrees(heading), 0, 1, 0)
    draw_fn()
    glPopMatrix()


def _box_local(sx: float, sy: float, sz: float, y: float, r: float, g: float, b: float, *, lx: float = 0, lz: float = 0) -> None:
    _draw_box(Box3D(lx, y, lz, sx, sy, sz, r, g, b))


def draw_vehicle_detailed(vehicle: Vehicle, brightness: float = 1.0) -> None:
    """Oriented vehicle mesh with body, cabin, wheels, and lights."""
    r, g, b = vehicle.color

    def draw_car() -> None:
        body_y = 0.45
        _box_local(1.75, 0.55, 3.6, body_y, r * brightness, g * brightness, b * brightness)
        # Cabin / glass
        _box_local(1.55, 0.45, 1.8, body_y + 0.55, 0.25 * brightness, 0.32 * brightness, 0.42 * brightness, lz=-0.2)
        # Hood / trunk hints
        _box_local(1.6, 0.12, 0.7, body_y + 0.2, r * 0.9 * brightness, g * 0.9 * brightness, b * 0.9 * brightness, lz=1.35)
        _box_local(1.6, 0.12, 0.7, body_y + 0.2, r * 0.85 * brightness, g * 0.85 * brightness, b * 0.85 * brightness, lz=-1.35)
        # Headlights
        _box_local(0.25, 0.12, 0.12, body_y + 0.15, 0.95 * brightness, 0.92 * brightness, 0.55 * brightness, lx=0.65, lz=1.78)
        _box_local(0.25, 0.12, 0.12, body_y + 0.15, 0.95 * brightness, 0.92 * brightness, 0.55 * brightness, lx=-0.65, lz=1.78)
        # Taillights
        _box_local(0.2, 0.1, 0.08, body_y + 0.15, 0.9 * brightness, 0.15 * brightness, 0.12 * brightness, lx=0.6, lz=-1.78)
        _box_local(0.2, 0.1, 0.08, body_y + 0.15, 0.9 * brightness, 0.15 * brightness, 0.12 * brightness, lx=-0.6, lz=-1.78)
        # Wheels
        for lx, lz in ((0.75, 1.1), (-0.75, 1.1), (0.75, -1.1), (-0.75, -1.1)):
            _box_local(0.28, 0.28, 0.28, 0.14, 0.12 * brightness, 0.12 * brightness, 0.12 * brightness, lx=lx, lz=lz)
        if vehicle.kind == TAXI:
            _box_local(1.5, 0.08, 2.8, body_y + 0.85, 0.95 * brightness, 0.82 * brightness, 0.1 * brightness)
            _box_local(0.5, 0.35, 0.5, body_y + 1.05, 0.15 * brightness, 0.15 * brightness, 0.15 * brightness)

    def draw_bus() -> None:
        _box_local(2.3, 1.1, 7.5, 1.1, r * brightness, g * brightness, b * brightness)
        for i in range(5):
            _box_local(2.0, 0.55, 1.0, 1.35, 0.45 * brightness, 0.58 * brightness, 0.72 * brightness, lz=-2.8 + i * 1.4)
        for lx, lz in ((0.9, 2.6), (-0.9, 2.6), (0.9, -2.6), (-0.9, -2.6)):
            _box_local(0.35, 0.35, 0.35, 0.18, 0.1 * brightness, 0.1 * brightness, 0.1 * brightness, lx=lx, lz=lz)

    def draw_bike() -> None:
        _box_local(0.12, 0.5, 1.1, 0.55, r * brightness, g * brightness, b * brightness)
        _box_local(0.5, 0.5, 0.5, 0.5, 0.2 * brightness, 0.2 * brightness, 0.2 * brightness, lz=0.55)
        _box_local(0.5, 0.5, 0.5, 0.5, 0.2 * brightness, 0.2 * brightness, 0.2 * brightness, lz=-0.55)

    if vehicle.kind == BUS:
        _with_transform(vehicle.x, vehicle.z, vehicle.heading, draw_bus)
    elif vehicle.kind == BIKE:
        _with_transform(vehicle.x, vehicle.z, vehicle.heading, draw_bike)
    else:
        _with_transform(vehicle.x, vehicle.z, vehicle.heading, draw_car)


def draw_pedestrian(npc: NPC, brightness: float = 1.0) -> None:
    """Simple humanoid — head, torso, legs; oriented along movement."""
    r, g, b = npc.color
    heading = 0.0
    if npc.path and npc.path_index < len(npc.path):
        tx, tz = npc.path[npc.path_index]
        heading = math.atan2(tx - npc.x, tz - npc.z)
    elif npc.path_index > 0 and npc.path:
        tx, tz = npc.path[npc.path_index - 1]
        heading = math.atan2(tx - npc.x, tz - npc.z)

    skin = (0.92 * brightness, 0.78 * brightness, 0.65 * brightness)
    pants = (0.25 * brightness, 0.28 * brightness, 0.35 * brightness)

    def draw_body() -> None:
        _draw_humanoid(
            jacket=(r * brightness, g * brightness, b * brightness),
            pants=pants,
            skin=skin,
            leg_swing=0.0,
            arm_swing=0.0,
            bob=0.0,
            hat="commuter" if npc.personality == "commuter" else "tourist" if npc.personality == "tourist" else None,
            umbrella=npc.has_umbrella,
            brightness=brightness,
        )

    _with_transform(npc.x, npc.z, heading, draw_body)


def draw_player_avatar(
    x: float,
    y: float,
    z: float,
    yaw: float,
    avatar,
    *,
    brightness: float = 1.0,
) -> None:
    """Draw the player character on the ground (third-person view)."""
    skin = (0.93 * brightness, 0.80 * brightness, 0.68 * brightness)
    jacket = tuple(c * brightness for c in avatar.jacket)
    pants = tuple(c * brightness for c in avatar.pants)

    def draw_body() -> None:
        _draw_humanoid(
            jacket=jacket,
            pants=pants,
            skin=skin,
            leg_swing=avatar.leg_swing,
            arm_swing=avatar.arm_swing,
            bob=avatar.bob,
            hat="player",
            umbrella=False,
            brightness=brightness,
        )

    _with_transform(x, z, yaw, draw_body)


def _draw_humanoid(
    *,
    jacket: tuple[float, float, float],
    pants: tuple[float, float, float],
    skin: tuple[float, float, float],
    leg_swing: float,
    arm_swing: float,
    bob: float,
    hat: str | None,
    umbrella: bool,
    brightness: float,
) -> None:
    # Legs (swing forward/back when walking)
    _box_local(0.20, 0.46, 0.20, 0.22 + bob, *pants, lx=-0.12, lz=leg_swing)
    _box_local(0.20, 0.46, 0.20, 0.22 + bob, *pants, lx=0.12, lz=-leg_swing)
    # Torso
    _box_local(0.44, 0.56, 0.30, 0.74 + bob, *jacket)
    # Arms
    _box_local(0.13, 0.44, 0.13, 0.70 + bob, *(jacket[0] * 0.92, jacket[1] * 0.92, jacket[2] * 0.92), lx=-0.34, lz=-arm_swing)
    _box_local(0.13, 0.44, 0.13, 0.70 + bob, *(jacket[0] * 0.92, jacket[1] * 0.92, jacket[2] * 0.92), lx=0.34, lz=arm_swing)
    # Head
    _box_local(0.30, 0.30, 0.30, 1.14 + bob, *skin)
    if hat == "player":
        _box_local(0.32, 0.10, 0.32, 1.32 + bob, 0.18 * brightness, 0.20 * brightness, 0.28 * brightness)
    elif hat == "commuter":
        _box_local(0.30, 0.08, 0.30, 1.28 + bob, 0.2 * brightness, 0.2 * brightness, 0.22 * brightness)
    elif hat == "tourist":
        _box_local(0.34, 0.1, 0.34, 1.30 + bob, 0.85 * brightness, 0.7 * brightness, 0.2 * brightness)
    if umbrella:
        _box_local(0.06, 0.7, 0.06, 1.35, 0.35 * brightness, 0.35 * brightness, 0.38 * brightness)
        _box_local(0.9, 0.06, 0.9, 1.42, 0.85 * brightness, 0.2 * brightness, 0.2 * brightness)

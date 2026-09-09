"""OpenGL rendering for the living city."""

from __future__ import annotations

import math

from nyc_world.map.buildings import Building3D
from nyc_world.city.landmarks import CAFE, LANDMARK, PARK, STORE, SUBWAY, Landmark3D
from nyc_world.city.npcs import NPC
from nyc_world.city.streets import Quad, StreetScene, TrafficLight3D
from nyc_world.city.vehicles import BIKE, BUS, CAR, TAXI, Vehicle
from nyc_world.core.world_3d import Box3D
from nyc_world.city.world_clock import WorldClock


def setup_gl(width: int, height: int, fov: float = 70.0) -> None:
    from OpenGL.GL import (
        GL_CULL_FACE,
        GL_DEPTH_TEST,
        GL_LEQUAL,
        GL_SMOOTH,
        glClearColor,
        glClearDepth,
        glCullFace,
        glDepthFunc,
        glEnable,
        glHint,
        glLoadIdentity,
        glMatrixMode,
        glShadeModel,
        glViewport,
    )
    from OpenGL.GLU import gluPerspective

    glViewport(0, 0, width, height)
    glMatrixMode(0x1701)
    glLoadIdentity()
    gluPerspective(fov, width / height if height else 1, 0.5, 2500.0)
    glMatrixMode(0x1700)
    glEnable(GL_DEPTH_TEST)
    glDepthFunc(GL_LEQUAL)
    glEnable(GL_CULL_FACE)
    glCullFace(0x0405)
    glClearColor(0.53, 0.73, 0.92, 1.0)
    glClearDepth(1.0)
    glShadeModel(GL_SMOOTH)
    glHint(0x0C51, 0x1102)
    # Manual per-vertex colors — fixed-function lighting is slower and redundant here.


def _enable_scene_lighting() -> None:
    """Soft directional light so buildings and characters have readable depth."""
    from OpenGL.GL import (
        GL_AMBIENT,
        GL_AMBIENT_AND_DIFFUSE,
        GL_COLOR_MATERIAL,
        GL_DIFFUSE,
        GL_FRONT_AND_BACK,
        GL_LIGHT0,
        GL_LIGHTING,
        GL_POSITION,
        GLfloat,
        glColorMaterial,
        glEnable,
        glLightfv,
    )

    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_COLOR_MATERIAL)
    glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
    glLightfv(GL_LIGHT0, GL_AMBIENT, (GLfloat * 4)(0.35, 0.35, 0.38, 1.0))
    glLightfv(GL_LIGHT0, GL_DIFFUSE, (GLfloat * 4)(0.72, 0.70, 0.66, 1.0))
    glLightfv(GL_LIGHT0, GL_POSITION, (GLfloat * 4)(0.45, 0.85, 0.35, 0.0))


def apply_environment(clock: WorldClock) -> None:
    from OpenGL.GL import glClearColor, glFogf, glFogi, glEnable, glDisable, GL_FOG, GL_EXP2

    r, g, b = clock.sky_color()
    bright = clock.ambient_brightness()
    glClearColor(r * bright, g * bright, b * bright, 1.0)
    density = clock.fog_density()
    if density > 0:
        glEnable(GL_FOG)
        glFogi(0x0B65, GL_EXP2)
        glFogf(0x0B62, density)
        glFogf(0x0B63, density * 0.5)
    else:
        glDisable(GL_FOG)


def _draw_quad(q: Quad) -> None:
    from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

    glColor3f(q.r, q.g, q.b)
    glBegin(GL_QUADS)
    glVertex3f(q.x0, q.y, q.z0)
    glVertex3f(q.x1, q.y, q.z1)
    glVertex3f(q.x2, q.y, q.z2)
    glVertex3f(q.x3, q.y, q.z3)
    glEnd()


def _draw_quad_batch(quads: list[Quad], brightness: float = 1.0) -> None:
    """Draw many quads in one glBegin block (same layer, fewer driver calls)."""
    if not quads:
        return
    from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

    glBegin(GL_QUADS)
    for q in quads:
        glColor3f(q.r * brightness, q.g * brightness, q.b * brightness)
        glVertex3f(q.x0, q.y, q.z0)
        glVertex3f(q.x1, q.y, q.z1)
        glVertex3f(q.x2, q.y, q.z2)
        glVertex3f(q.x3, q.y, q.z3)
    glEnd()


_street_list_id: int | None = None
_street_scene_id: int | None = None


def _draw_streets_cached(scene: StreetScene, brightness: float = 1.0) -> None:
    global _street_list_id, _street_scene_id
    from OpenGL.GL import GL_COMPILE, glCallList, glEndList, glGenLists, glNewList

    scene_key = id(scene)
    if _street_list_id is None or _street_scene_id != scene_key or abs(brightness - 1.0) >= 0.02:
        if _street_list_id is not None:
            from OpenGL.GL import glDeleteLists

            glDeleteLists(_street_list_id, 1)
        _street_list_id = glGenLists(1)
        glNewList(_street_list_id, GL_COMPILE)
        _draw_quad_batch(scene.sidewalk_quads, brightness)
        _draw_quad_batch(scene.curb_quads, brightness)
        _draw_quad_batch(scene.road_quads, brightness)
        _draw_quad_batch(scene.marking_quads, brightness)
        _draw_quad_batch(scene.crosswalk_quads, brightness)
        for light in scene.traffic_lights:
            draw_traffic_light(light, brightness)
        glEndList()
        _street_scene_id = scene_key
    glCallList(_street_list_id)


def draw_streets(scene: StreetScene, brightness: float = 1.0) -> None:
    _draw_streets_cached(scene, brightness)


def draw_traffic_light(light: TrafficLight3D, brightness: float = 1.0) -> None:
    from nyc_world.core.world_3d import Box3D
    draw_box(Box3D(light.x, light.height / 2, light.z, 0.2, light.height, 0.2,
                   0.35 * brightness, 0.36 * brightness, 0.38 * brightness))
    draw_box(Box3D(light.x, light.height - 0.3, light.z, 0.35, 0.5, 0.2,
                   0.2, 0.2, 0.2))
    draw_box(Box3D(light.x, light.height - 0.1, light.z, 0.12, 0.12, 0.12, 0.9, 0.2, 0.2))


def draw_box(box: Box3D) -> None:
    from OpenGL.GL import GL_QUADS, glBegin, glColor3f, glEnd, glVertex3f

    hx, hy, hz = box.sx / 2, box.sy / 2, box.sz / 2
    x, y, z = box.x, box.y, box.z
    glColor3f(box.r, box.g, box.b)
    glBegin(GL_QUADS)
    glVertex3f(x - hx, y + hy, z - hz)
    glVertex3f(x - hx, y + hy, z + hz)
    glVertex3f(x + hx, y + hy, z + hz)
    glVertex3f(x + hx, y + hy, z - hz)
    glVertex3f(x - hx, y - hy, z - hz)
    glVertex3f(x + hx, y - hy, z - hz)
    glVertex3f(x + hx, y - hy, z + hz)
    glVertex3f(x - hx, y - hy, z + hz)
    glVertex3f(x - hx, y - hy, z + hz)
    glVertex3f(x + hx, y - hy, z + hz)
    glVertex3f(x + hx, y + hy, z + hz)
    glVertex3f(x - hx, y + hy, z + hz)
    glVertex3f(x - hx, y - hy, z - hz)
    glVertex3f(x - hx, y + hy, z - hz)
    glVertex3f(x + hx, y + hy, z - hz)
    glVertex3f(x + hx, y - hy, z - hz)
    glVertex3f(x + hx, y - hy, z - hz)
    glVertex3f(x + hx, y + hy, z - hz)
    glVertex3f(x + hx, y + hy, z + hz)
    glVertex3f(x + hx, y - hy, z + hz)
    glVertex3f(x - hx, y - hy, z - hz)
    glVertex3f(x - hx, y - hy, z + hz)
    glVertex3f(x - hx, y + hy, z + hz)
    glVertex3f(x - hx, y + hy, z - hz)
    glEnd()


from nyc_world.render.meshes import classify_building_details, cull_buildings


def draw_building(
    building: Building3D,
    brightness: float = 1.0,
    *,
    player_x: float | None = None,
    player_z: float | None = None,
    force_detail: str | None = None,
    detail: str | None = None,
) -> None:
    from nyc_world.render.meshes import draw_building_detailed

    draw_building_detailed(
        building,
        brightness,
        detail=detail or force_detail or "simple",
        player_x=player_x,
        player_z=player_z,
    )


def draw_far_buildings(
    buildings: list[Building3D],
    brightness: float = 1.0,
    *,
    player_x: float = 0.0,
    player_z: float = 0.0,
) -> None:
    from nyc_world.render.meshes import MAX_SKYLINE_BUILDINGS, _building_dist_sq, draw_building_detailed

    if len(buildings) > MAX_SKYLINE_BUILDINGS:
        buildings = sorted(buildings, key=lambda b: _building_dist_sq(b, player_x, player_z))[
            :MAX_SKYLINE_BUILDINGS
        ]
    for building in buildings:
        draw_building_detailed(building, brightness, detail="skyline")


def draw_landmark(lm: Landmark3D, brightness: float = 1.0) -> None:
    x, z, h = lm.x, lm.z, lm.height
    if lm.kind == CAFE:
        draw_box(Box3D(x, 1.2, z, 2.5, 2.4, 2.5, 0.55 * brightness, 0.35 * brightness, 0.25 * brightness))
        draw_box(Box3D(x, 2.8, z, 0.8, 0.8, 0.3, 0.9 * brightness, 0.85 * brightness, 0.7 * brightness))
    elif lm.kind == SUBWAY:
        draw_box(Box3D(x, 0.15, z, 4, 0.3, 4, 0.1 * brightness, 0.55 * brightness, 0.2 * brightness))
        draw_box(Box3D(x, 1.5, z, 2, 3, 2, 0.15 * brightness, 0.45 * brightness, 0.18 * brightness))
    elif lm.kind == PARK:
        draw_box(Box3D(x, 0.5, z, 1.5, 1, 0.3, 0.4 * brightness, 0.3 * brightness, 0.2 * brightness))
    elif lm.kind == STORE:
        draw_box(Box3D(x, 1.5, z, 3, 3, 2.5, 0.7 * brightness, 0.5 * brightness, 0.4 * brightness))
        draw_box(Box3D(x, 2.5, z, 3.2, 0.3, 2.7, 0.9 * brightness, 0.2 * brightness, 0.15 * brightness))
    else:
        draw_box(Box3D(x, h / 2, z, 2, h, 2, 0.85 * brightness, 0.75 * brightness, 0.3 * brightness))


def draw_npc(npc: NPC, brightness: float = 1.0) -> None:
    from nyc_world.render.meshes import draw_pedestrian

    draw_pedestrian(npc, brightness)


def draw_npc_colored(npc: NPC, brightness: float, color: tuple[float, float, float]) -> None:
    old = npc.color
    npc.color = color
    draw_npc(npc, brightness)
    npc.color = old


def _draw_selection_marker(x: float, y: float, z: float) -> None:
    draw_box(Box3D(x, y, z, 0.5, 0.5, 0.5, 1.0, 0.85, 0.15))


def draw_vehicle(vehicle: Vehicle, brightness: float = 1.0) -> None:
    from nyc_world.render.meshes import draw_vehicle_detailed

    draw_vehicle_detailed(vehicle, brightness)


def _draw_vehicle_simple(vehicle: Vehicle, brightness: float = 1.0) -> None:
    r, g, b = vehicle.color
    if vehicle.kind == BIKE:
        draw_box(Box3D(vehicle.x, 0.5, vehicle.z, 0.4, 1.0, 1.2, r * brightness, g * brightness, b * brightness))
    elif vehicle.kind == BUS:
        draw_box(Box3D(vehicle.x, 1.2, vehicle.z, 2.2, 2.4, 6, r * brightness, g * brightness, b * brightness))
    else:
        draw_box(Box3D(vehicle.x, 0.6, vehicle.z, 1.8, 1.2, 3.5, r * brightness, g * brightness, b * brightness))
    if vehicle.kind == TAXI:
        draw_box(Box3D(vehicle.x, 1.3, vehicle.z, 1.6, 0.3, 3.2, 0.95 * brightness, 0.85 * brightness, 0.1 * brightness))


def render_interior_frame(
    interior_boxes: list[Box3D],
    px: float,
    py: float,
    pz: float,
    yaw: float,
    pitch: float,
    *,
    avatar=None,
    moving: bool = False,
    sprinting: bool = False,
    brightness: float = 1.0,
) -> None:
    """Render a simple interior room instead of the city."""
    from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClear, glClearColor, glLoadIdentity

    from nyc_world.render.camera import apply_third_person_camera

    glClearColor(0.35, 0.32, 0.30, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    apply_third_person_camera(px, py, pz, yaw, pitch)
    for box in interior_boxes:
        draw_box(box)
    if avatar is not None:
        from nyc_world.render.meshes import draw_player_avatar

        draw_player_avatar(px, py, pz, avatar.facing_yaw, avatar, brightness=brightness)


def render_frame(
    clock: WorldClock,
    streets: StreetScene | None,
    buildings: list[Building3D],
    landmarks: list[Landmark3D],
    props: list[Box3D],
    npcs: list[NPC],
    vehicles: list[Vehicle],
    px: float,
    py: float,
    pz: float,
    yaw: float,
    pitch: float,
    *,
    far_buildings: list[Building3D] | None = None,
    building_draw_radius_m: float | None = 200.0,
    draw_far_skyline: bool = False,
    camera_footprint=None,
    avatar=None,
    twin=None,
    photo=None,
    minds=None,
    selected_id: str | None = None,
) -> None:
    from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClear, glLoadIdentity

    from nyc_world.render.camera import apply_third_person_camera, apply_twin_camera

    render_clock = photo.visual_clock(clock) if photo and photo.active else clock
    apply_environment(render_clock)
    bright = render_clock.ambient_brightness()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    if photo and photo.active:
        photo.camera.apply()
    elif twin and twin.active:
        apply_twin_camera(
            px, py, pz, yaw, height=twin.camera_height, distance=twin.camera_distance
        )
    else:
        apply_third_person_camera(
            px, py, pz, yaw, pitch, camera_footprint=camera_footprint
        )

    building_details = classify_building_details(buildings, px, pz)
    visible_buildings = cull_buildings(
        buildings, px, pz, max_radius_m=building_draw_radius_m
    )
    if streets:
        draw_streets(streets, bright)
    from OpenGL.GL import GL_CULL_FACE, glDisable, glEnable

    glDisable(GL_CULL_FACE)
    for building in visible_buildings:
        draw_building(
            building,
            bright,
            player_x=px,
            player_z=pz,
            detail=building_details.get(id(building), "simple"),
        )
    if draw_far_skyline and far_buildings:
        draw_far_buildings(far_buildings, bright, player_x=px, player_z=pz)
    glEnable(GL_CULL_FACE)
    for prop in props:
        draw_box(prop)
    for lm in landmarks:
        draw_landmark(lm, bright)
    for npc in npcs:
        if twin and twin.active and twin.heatmap and minds:
            nearby = sum(
                1
                for other in npcs
                if other.name != npc.name
                and (other.x - npc.x) ** 2 + (other.z - npc.z) ** 2 < 400
            )
            color = twin.heatmap_color(npc, minds=minds, nearby_count=nearby)
            draw_npc_colored(npc, bright, color)
        else:
            draw_npc(npc, bright)
        if selected_id and npc.name == selected_id:
            _draw_selection_marker(npc.x, 2.5, npc.z)
    for i, vehicle in enumerate(vehicles):
        draw_vehicle(vehicle, bright)
        if selected_id and selected_id == f"vehicle_{i}":
            _draw_selection_marker(vehicle.x, 2.5, vehicle.z)
    if avatar is not None and not (twin and twin.active) and not (photo and photo.active):
        from nyc_world.render.meshes import draw_player_avatar

        draw_player_avatar(px, py, pz, avatar.facing_yaw, avatar, brightness=bright)

    if photo and photo.active and photo.vignette > 0:
        _draw_vignette(photo.vignette)


def _draw_vignette(strength: float) -> None:
    """Radial edge darkening for photo mode (cheap fake DoF)."""
    from OpenGL.GL import (
        GL_BLEND,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_SRC_ALPHA,
        GL_DISABLE,
        glBegin,
        glBlendFunc,
        glColor4f,
        glEnable,
        glEnd,
        glMatrixMode,
        glLoadIdentity,
        glPopMatrix,
        glPushMatrix,
        GL_PROJECTION,
        GL_MODELVIEW,
        GL_QUADS,
    )

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    alpha = 0.15 + strength * 0.55
    glColor4f(0.0, 0.0, 0.0, alpha)
    glBegin(GL_QUADS)
    for x0, y0, x1, y1 in ((-1, -1, 1, -0.55), (-1, 0.55, 1, 1), (-1, -0.55, -0.65, 0.55), (0.65, -0.55, 1, 0.55)):
        glVertex2f(x0, y0)
        glVertex2f(x1, y0)
        glVertex2f(x1, y1)
        glVertex2f(x0, y1)
    glEnd()
    glDisable(GL_BLEND)
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

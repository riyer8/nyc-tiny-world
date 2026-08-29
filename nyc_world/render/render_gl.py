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


def draw_streets(scene: StreetScene, brightness: float = 1.0) -> None:
    for q in scene.sidewalk_quads:
        _draw_quad(Quad(q.x0, q.z0, q.x1, q.z1, q.x2, q.z2, q.x3, q.z3, q.y,
                        q.r * brightness, q.g * brightness, q.b * brightness))
    for q in scene.road_quads:
        _draw_quad(q)
    for q in scene.crosswalk_quads:
        _draw_quad(q)
    for q in scene.marking_quads:
        _draw_quad(q)
    for light in scene.traffic_lights:
        draw_traffic_light(light, brightness)


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


def draw_building(building: Building3D, brightness: float = 1.0) -> None:
    from OpenGL.GL import GL_QUADS, GL_TRIANGLE_FAN, glBegin, glColor3f, glEnd, glVertex3f

    fp = building.footprint
    if len(fp) < 3:
        return
    h = building.height
    glColor3f(building.wall_r * brightness, building.wall_g * brightness, building.wall_b * brightness)
    glBegin(GL_QUADS)
    for i in range(len(fp)):
        x0, z0 = fp[i]
        x1, z1 = fp[(i + 1) % len(fp)]
        glVertex3f(x0, 0, z0)
        glVertex3f(x1, 0, z1)
        glVertex3f(x1, h, z1)
        glVertex3f(x0, h, z0)
    glEnd()
    glColor3f(building.roof_r * brightness, building.roof_g * brightness, building.roof_b * brightness)
    glBegin(GL_TRIANGLE_FAN)
    glVertex3f(fp[0][0], h, fp[0][1])
    for x, z in fp[1:]:
        glVertex3f(x, h, z)
    glEnd()


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
    r, g, b = npc.color
    draw_box(Box3D(npc.x, 0.85, npc.z, 0.5, 1.7, 0.5, r * brightness, g * brightness, b * brightness))
    if npc.has_umbrella:
        draw_box(Box3D(npc.x, 2.0, npc.z, 1.2, 0.08, 1.2, 0.9 * brightness, 0.2 * brightness, 0.2 * brightness))


def draw_vehicle(vehicle: Vehicle, brightness: float = 1.0) -> None:
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
) -> None:
    """Render a simple interior room instead of the city."""
    from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClear, glClearColor, glLoadIdentity, glRotatef, glTranslatef

    glClearColor(0.35, 0.32, 0.30, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glRotatef(math.degrees(pitch), 1, 0, 0)
    glRotatef(math.degrees(yaw), 0, 1, 0)
    glTranslatef(-px, -py, -pz)
    for box in interior_boxes:
        draw_box(box)


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
) -> None:
    from OpenGL.GL import GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClear, glLoadIdentity, glRotatef, glTranslatef

    apply_environment(clock)
    bright = clock.ambient_brightness()
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glRotatef(math.degrees(pitch), 1, 0, 0)
    glRotatef(math.degrees(yaw), 0, 1, 0)
    glTranslatef(-px, -py, -pz)

    if streets:
        draw_streets(streets, bright)
    for building in buildings:
        draw_building(building, bright)
    for prop in props:
        draw_box(prop)
    for lm in landmarks:
        draw_landmark(lm, bright)
    for npc in npcs:
        draw_npc(npc, bright)
    for vehicle in vehicles:
        draw_vehicle(vehicle, bright)

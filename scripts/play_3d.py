#!/usr/bin/env python3
"""Walk around NYC neighborhoods in 3D — living city edition."""

from __future__ import annotations

import math
import sys

import _bootstrap  # noqa: F401
import pygame
from pygame.locals import DOUBLEBUF, K_ESCAPE, K_a, K_d, K_s, K_w, OPENGL, QUIT, RESIZABLE

from nyc_world.city_sim import CitySimulation
from nyc_world.paths import DEFAULT_MAP_PATH
from nyc_world.render_gl import render_frame, setup_gl
from nyc_world.world import World
from nyc_world.world_3d import EYE_HEIGHT, World3D

FPS = 60
MOVE_SPEED = 6.0
MOUSE_SENS = 0.0025


def main() -> None:
    if not DEFAULT_MAP_PATH.exists():
        print("No map found. Run: python3 scripts/generate_map.py")
        sys.exit(1)

    pygame.init()
    width, height = 960, 720
    screen = pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF | RESIZABLE)
    pygame.display.set_caption("NYC Tiny World 3D")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)
    setup_gl(width, height)

    world = World.from_file(DEFAULT_MAP_PATH)
    world3d = World3D(world)
    px, py, pz = world3d.spawn
    prev_x, prev_z = px, pz
    yaw = math.pi
    pitch = 0.0

    city: CitySimulation | None = None
    if world.projection:
        city = CitySimulation(world.projection, px, pz)
        print(f"City loaded: {city.summary()}")

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == K_ESCAPE:
                running = False
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.size
                screen = pygame.display.set_mode(
                    (width, height), OPENGL | DOUBLEBUF | RESIZABLE
                )
                setup_gl(width, height)

        if city:
            city.update(dt)

        mx, my = pygame.mouse.get_rel()
        yaw -= mx * MOUSE_SENS
        pitch -= my * MOUSE_SENS
        pitch = max(-1.4, min(1.4, pitch))

        keys = pygame.key.get_pressed()
        move_x = move_z = 0.0
        if keys[K_w]:
            move_x += math.sin(yaw)
            move_z += math.cos(yaw)
        if keys[K_s]:
            move_x -= math.sin(yaw)
            move_z -= math.cos(yaw)
        if keys[K_a]:
            move_x -= math.cos(yaw)
            move_z += math.sin(yaw)
        if keys[K_d]:
            move_x += math.cos(yaw)
            move_z -= math.sin(yaw)

        if move_x or move_z:
            length = math.hypot(move_x, move_z)
            move_x = move_x / length * MOVE_SPEED * dt
            move_z = move_z / length * MOVE_SPEED * dt
            new_x = px + move_x
            new_z = pz + move_z
            px, pz = world3d.resolve_move(prev_x, prev_z, new_x, new_z)
            prev_x, prev_z = px, pz

        py = EYE_HEIGHT
        sim_clock = city.clock if city else None
        from nyc_world.world_clock import WorldClock

        render_frame(
            clock=sim_clock or WorldClock(),
            streets=city.street_scene if city else None,
            buildings=world3d.buildings,
            landmarks=city.landmarks if city else [],
            props=world3d.boxes,
            npcs=city.npcs if city else [],
            vehicles=city.vehicles if city else [],
            px=px,
            py=py,
            pz=pz,
            yaw=yaw,
            pitch=pitch,
        )
        pygame.display.flip()

        if world.projection and city:
            gx = px / world3d.meters_per_tile * world.tile_size
            gy = (world.rows - pz / world3d.meters_per_tile) * world.tile_size
            lat, lon = world.projection.to_gps(gx, gy)
            weather = city.clock.weather.value
            pygame.display.set_caption(
                f"NYC Tiny World — {city.clock.time_str} {weather} — {lat:.5f}, {lon:.5f}"
            )

    pygame.quit()


if __name__ == "__main__":
    main()

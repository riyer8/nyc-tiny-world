#!/usr/bin/env python3
"""Walk around NYC neighborhoods in 3D — living city edition."""

from __future__ import annotations

import math
import sys

import _bootstrap  # noqa: F401
import pygame
from pygame.locals import (
    DOUBLEBUF,
    K_ESCAPE,
    K_e,
    KEYDOWN,
    OPENGL,
    QUIT,
    RESIZABLE,
)

from nyc_world.city import CitySimulation
from nyc_world.core import EYE_HEIGHT, World, World3D
from nyc_world.game import CONTROLS_HELP, GameSession, world_speed_multiplier
from nyc_world.game.controls import movement_delta_3d, read_movement
from nyc_world.paths import DEFAULT_MAP_PATH
from nyc_world.render import draw_hud, render_frame, render_interior_frame, setup_gl

FPS = 60
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
    session: GameSession | None = None
    if world.projection:
        city = CitySimulation(world.projection, px, pz)
        session = GameSession(city, px, pz)
        print(f"City loaded: {city.summary()}")
        print("Quest: Walk to Maya (pink NPC near spawn) and press E to start.")
        print(CONTROLS_HELP)

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_e and session:
                    new_pos = session.press_interact(px, pz)
                    if new_pos:
                        px, pz = new_pos
                        prev_x, prev_z = px, pz
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.size
                screen = pygame.display.set_mode(
                    (width, height), OPENGL | DOUBLEBUF | RESIZABLE
                )
                setup_gl(width, height)

        keys = pygame.key.get_pressed()
        movement = read_movement(keys)
        in_interior = session is not None and session.in_interior

        if city and not in_interior:
            city.update(dt, speed_multiplier=world_speed_multiplier(movement.sprint))

        mx, my = pygame.mouse.get_rel()
        yaw -= mx * MOUSE_SENS
        pitch -= my * MOUSE_SENS
        pitch = max(-1.4, min(1.4, pitch))

        move_x, move_z = movement_delta_3d(movement, yaw, dt=dt)
        if move_x or move_z:
            new_x = px + move_x
            new_z = pz + move_z
            if in_interior and session:
                px, pz = session.clamp_interior(new_x, new_z)
            else:
                px, pz = world3d.resolve_move(prev_x, prev_z, new_x, new_z)
            prev_x, prev_z = px, pz

        py = EYE_HEIGHT
        from nyc_world.city.world_clock import WorldClock

        sim_clock = city.clock if city else None

        if in_interior and session and session.current_interior:
            render_interior_frame(
                session.current_interior.build_boxes(),
                px,
                py,
                pz,
                yaw,
                pitch,
            )
        else:
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

        if session:
            session.update(px, pz)
            session.hud.controls_hint = CONTROLS_HELP
            session.hud.sprinting = movement.sprint
            draw_hud(width, height, session.hud)

        pygame.display.flip()

        if world.projection and city:
            gx = px / world3d.meters_per_tile * world.tile_size
            gy = (world.rows - pz / world3d.meters_per_tile) * world.tile_size
            lat, lon = world.projection.to_gps(gx, gy)
            weather = city.clock.weather.value
            quest = session.quest_summary() if session else ""
            speed = "SPRINT" if movement.sprint else "walk"
            pygame.display.set_caption(
                f"NYC Tiny World — {city.clock.time_str} {weather} — {speed} — "
                f"{lat:.5f}, {lon:.5f} — {quest}"
            )

    pygame.quit()


if __name__ == "__main__":
    main()

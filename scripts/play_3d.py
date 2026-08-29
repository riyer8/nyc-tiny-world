#!/usr/bin/env python3
"""Walk around NYC neighborhoods in 3D — living city edition."""

from __future__ import annotations

import argparse
import math
import sys

import _bootstrap  # noqa: F401
import pygame
from pygame.locals import (
    DOUBLEBUF,
    K_ESCAPE,
    K_SPACE,
    K_e,
    K_g,
    KEYDOWN,
    MOUSEBUTTONDOWN,
    OPENGL,
    QUIT,
    RESIZABLE,
)

from nyc_world.core import EYE_HEIGHT, World, World3D
from nyc_world.game import CONTROLS_HELP_3D, GameSession, world_speed_multiplier
from nyc_world.game.controls import JumpState, MouseLook, movement_delta_3d, read_movement
from nyc_world.geo import build_minimap, locate_player
from nyc_world.paths import DEFAULT_MAP_PATH
from nyc_world.render import draw_hud, render_frame, render_interior_frame, setup_gl
from nyc_world.streaming import StreamingWorldManager

FPS = 60


def _set_mouse_look(active: bool) -> None:
    pygame.mouse.set_visible(not active)
    pygame.event.set_grab(active)
    pygame.mouse.get_rel()


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk NYC in 3D.")
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record (state, action, next_state) trajectories to data/trajectories/",
    )
    args = parser.parse_args()

    if not DEFAULT_MAP_PATH.exists():
        print("No map found. Run: python3 scripts/generate_map.py")
        sys.exit(1)

    pygame.init()
    width, height = 960, 720
    screen = pygame.display.set_mode((width, height), OPENGL | DOUBLEBUF | RESIZABLE)
    pygame.display.set_caption("NYC Tiny World 3D")
    _set_mouse_look(False)
    setup_gl(width, height)

    world = World.from_file(DEFAULT_MAP_PATH)
    world3d = World3D(world)
    px, py, pz = world3d.spawn
    prev_x, prev_z = px, pz
    frame_start_x, frame_start_z = px, pz
    yaw = math.pi
    pitch = 0.0
    mouse_look = MouseLook()
    jump = JumpState()
    show_geo_debug = False

    stream: StreamingWorldManager | None = None
    session: GameSession | None = None
    if world.projection:
        stream = StreamingWorldManager(
            world.projection,
            world3d.meters_per_tile,
            px,
            pz,
            world3d.buildings,
        )
        session = GameSession(
            stream.city,
            px,
            pz,
            record_trajectories=args.record,
        )
        print(f"Streaming world: {stream.summary()}")
        print(f"Simulation: tick 0, minds={len(stream.city.mind_registry.minds)}")
        if args.record:
            print("Recording trajectories to data/trajectories/")
        print("Quest: Walk to Maya (pink NPC near spawn) and press E to start.")
        print(CONTROLS_HELP_3D)
        print("Press G for location & simulation debug panel.")

    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        frame_start_x, frame_start_z = px, pz
        building_count = len(stream.render_buildings) if stream else len(world3d.buildings)

        if session:
            session.begin_frame(px, pz, yaw=yaw, building_count=building_count)

        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                elif event.key == K_SPACE:
                    jump.start_jump()
                elif event.key == K_g:
                    show_geo_debug = not show_geo_debug
                elif event.key == K_e and session:
                    new_pos = session.press_interact(px, pz)
                    if new_pos:
                        px, pz = new_pos
                        prev_x, prev_z = px, pz
                        frame_start_x, frame_start_z = px, pz
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                mouse_look.toggle()
                _set_mouse_look(mouse_look.active)
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.size
                screen = pygame.display.set_mode(
                    (width, height), OPENGL | DOUBLEBUF | RESIZABLE
                )
                setup_gl(width, height)

        keys = pygame.key.get_pressed()
        movement = read_movement(keys)
        in_interior = session is not None and session.in_interior
        speed_mult = world_speed_multiplier(movement.sprint)

        if stream and not in_interior:
            stream.update(dt, px, pz, speed_multiplier=speed_mult, tick_city=session is None)
            if session:
                session.simulation.advance_world(dt, speed_multiplier=speed_mult)

        mx, my = pygame.mouse.get_rel()
        yaw, pitch = mouse_look.apply(mx, my, yaw, pitch)

        move_x, move_z = movement_delta_3d(movement, yaw, dt=dt)
        if move_x or move_z:
            new_x = px + move_x
            new_z = pz + move_z
            if in_interior and session:
                px, pz = session.clamp_interior(new_x, new_z)
            else:
                px, pz = world3d.resolve_move(prev_x, prev_z, new_x, new_z)
            prev_x, prev_z = px, pz

        jump_height = jump.update(dt)
        py = EYE_HEIGHT + jump_height
        from nyc_world.city.world_clock import WorldClock

        sim_clock = stream.clock if stream else None

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
                streets=stream.street_scene if stream else None,
                buildings=stream.render_buildings if stream else world3d.buildings,
                landmarks=stream.render_landmarks if stream else [],
                props=world3d.boxes,
                npcs=stream.render_npcs if stream else [],
                vehicles=stream.render_vehicles if stream else [],
                px=px,
                py=py,
                pz=pz,
                yaw=yaw,
                pitch=pitch,
            )

        if session and world.projection and stream:
            session.end_frame(
                px,
                pz,
                yaw=yaw,
                dx=px - frame_start_x,
                dz=pz - frame_start_z,
                sprint=movement.sprint,
                jumped=jump.height > 0.0 or jump.velocity > 0.0,
                building_count=building_count,
            )
            location = locate_player(
                world.projection,
                world3d.meters_per_tile,
                px,
                pz,
                stream.streets,
                stream.city.landmarks,
            )
            session.hud.controls_hint = CONTROLS_HELP_3D
            session.hud.sprinting = movement.sprint
            session.hud.adjusting_view = mouse_look.active
            session.hud.show_geo_debug = show_geo_debug
            session.hud.player_lat = location.latitude
            session.hud.player_lon = location.longitude
            session.hud.nearest_street = location.nearest_street
            session.hud.nearest_poi = location.nearest_poi
            session.hud.neighborhood = location.neighborhood
            session.hud.borough = location.borough
            session.hud.streaming_tiles = len(stream.state.loaded_tile_ids)
            session.hud.streaming_buildings = stream.state.buildings_in_render
            if not in_interior:
                session.hud.minimap = build_minimap(
                    world,
                    world.projection,
                    world3d.meters_per_tile,
                    px,
                    pz,
                    yaw,
                    world3d.width_m,
                    world3d.depth_m,
                    streaming=stream.state,
                )
            else:
                session.hud.minimap = None
            draw_hud(width, height, session.hud)

            speed = "SPRINT" if movement.sprint else "walk"
            look = "look" if mouse_look.active else "locked"
            traj = session.hud.trajectory_steps
            pygame.display.set_caption(
                f"NYC Tiny World — {stream.clock.time_str} — {speed}/{look} — "
                f"{location.latitude:.5f}, {location.longitude:.5f} — "
                f"{len(stream.state.loaded_tile_ids)} tiles — "
                f"tick {session.simulation.tick} — "
                f"{traj} traj — "
                f"{session.quest_summary()}"
            )

        pygame.display.flip()

    if session:
        session.close()
    pygame.quit()


if __name__ == "__main__":
    main()

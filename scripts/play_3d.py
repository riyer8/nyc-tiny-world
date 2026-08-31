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
    K_BACKQUOTE,
    K_ESCAPE,
    K_SPACE,
    K_0,
    K_1,
    K_2,
    K_3,
    K_4,
    K_5,
    K_6,
    K_COMMA,
    K_PERIOD,
    K_d,
    K_e,
    K_f,
    K_g,
    K_h,
    K_i,
    K_j,
    K_m,
    K_n,
    K_o,
    K_p,
    K_r,
    K_RETURN,
    K_TAB,
    K_LEFTBRACKET,
    K_RIGHTBRACKET,
    K_EQUALS,
    K_MINUS,
    K_PLUS,
    K_s,
    K_t,
    K_v,
    K_w,
    K_x,
    K_y,
    KEYDOWN,
    KMOD_SHIFT,
    MOUSEBUTTONDOWN,
    MOUSEWHEEL,
    OPENGL,
    QUIT,
    RESIZABLE,
)

from pathlib import Path

from nyc_world.core import World, World3D
from nyc_world.game import CONTROLS_HELP_3D, GameSession, world_speed_multiplier
from nyc_world.game.controls import JumpState, MouseLook, movement_delta_3d, read_movement
from nyc_world.game.player_avatar import PlayerAvatar
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
    parser.add_argument(
        "--save-slot",
        default="default",
        help="Save file slot name (data/saves/<slot>.json)",
    )
    parser.add_argument(
        "--no-load",
        action="store_true",
        help="Start fresh without loading an existing save",
    )
    parser.add_argument(
        "--live-feeds",
        action="store_true",
        help="Poll live weather feeds (Open-Meteo) and apply to simulation",
    )
    parser.add_argument(
        "--feed-fixture",
        type=str,
        default="",
        help="Load feed data from a JSON fixture (e.g. tests/fixtures/feeds/mta_delay.json)",
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
    pitch = MouseLook().default_pitch
    mouse_look = MouseLook()
    jump = JumpState()
    avatar = PlayerAvatar()
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
        feed_fixture = Path(args.feed_fixture) if args.feed_fixture else None
        session = GameSession(
            stream.city,
            px,
            pz,
            record_trajectories=args.record,
            save_slot=args.save_slot,
            load_save=not args.no_load,
            live_feeds=args.live_feeds,
            feed_fixture=feed_fixture,
        )
        if session._loaded_position:
            px, pz = session._loaded_position
            prev_x, prev_z = px, pz
            frame_start_x, frame_start_z = px, pz
            print(f"Loaded save from {session.save_path}")
        print(f"Streaming world: {stream.summary()}")
        print(f"Simulation: tick 0, minds={len(stream.city.mind_registry.minds)}")
        if args.record:
            print("Recording trajectories to data/trajectories/")
        print("Quest: Walk to Maya (pink NPC near spawn) and press E to start.")
        print(CONTROLS_HELP_3D)
        print("Press G for location & simulation debug panel.")

    clock = pygame.time.Clock()
    running = True
    minimap_timer = 0.0
    minimap_interval = 0.25  # rebuild mini-map 4×/sec, not every frame

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
                    if session and session.in_subway_menu:
                        session.cancel_subway_menu()
                        session.update(px, pz, building_count=building_count, dt=dt)
                    else:
                        running = False
                elif event.key == K_SPACE:
                    if session and session.in_twin:
                        session.twin.toggle_pause()
                        session.update(px, pz, building_count=building_count, dt=dt)
                    else:
                        jump.start_jump()
                elif event.key == K_t and session:
                    session.toggle_twin()
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_h and session and session.in_twin:
                    session.twin.cycle_heatmap()
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_i and session and session.in_twin:
                    if session.imagine.active:
                        session.cycle_imagine_scenario()
                    else:
                        session.toggle_imagine()
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_r and session and session.imagine.active:
                    session.run_imagination(px, pz)
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif session and session.in_twin and event.key in (K_1, K_2, K_3) and not session.imagine.active:
                    scales = {K_1: 1.0, K_2: 10.0, K_3: 30.0}
                    session.twin.set_time_scale(scales[event.key])
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_g:
                    mods = pygame.key.get_mods()
                    if session and (mods & KMOD_SHIFT):
                        session.toggle_god()
                        session.update(px, pz, building_count=building_count, dt=dt)
                    else:
                        show_geo_debug = not show_geo_debug
                elif event.key == K_BACKQUOTE and session:
                    session.toggle_god()
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif session and session.in_god:
                    if event.key == K_6:
                        session.god_set_time(6, 0)
                    elif event.key == K_1:
                        session.god_set_time(12, 0)
                    elif event.key == K_0:
                        session.god_set_time(0, 0)
                    elif event.key == K_w:
                        session.god_set_weather("rain")
                    elif event.key == K_s:
                        session.god_set_weather("snow")
                    elif event.key == K_d:
                        session.god_set_weather("clear")
                    elif event.key == K_o:
                        session.god_set_weather("fog")
                    elif event.key == K_v:
                        session.god_spawn_festival(px, pz)
                    elif event.key == K_c:
                        session.god_close_road()
                    elif event.key == K_x:
                        session.god_clear_closures()
                    else:
                        continue
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_p and session:
                    active = session.toggle_photo(px, 2.0, pz, yaw=yaw, pitch=pitch)
                    if active:
                        mouse_look.active = True
                        _set_mouse_look(True)
                    else:
                        yaw, pitch = session.photo.restore_yaw_pitch()
                        mouse_look.active = False
                        _set_mouse_look(False)
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif session and session.in_photo:
                    if event.key == K_RETURN:
                        session.take_photo(width, height)
                    elif event.key == K_TAB:
                        session.photo.pause_simulation = not session.photo.pause_simulation
                    elif event.key == K_LEFTBRACKET:
                        session.photo.adjust_hour(-0.5)
                    elif event.key == K_RIGHTBRACKET:
                        session.photo.adjust_hour(0.5)
                    elif event.key == K_n:
                        session.photo.cycle_weather()
                    elif event.key in (K_EQUALS, K_PLUS):
                        session.photo.adjust_fov(3.0)
                        setup_gl(width, height, session.photo.camera.fov)
                    elif event.key == K_MINUS:
                        session.photo.adjust_fov(-3.0)
                        setup_gl(width, height, session.photo.camera.fov)
                    elif event.key == K_COMMA:
                        session.photo.adjust_vignette(-0.05)
                    elif event.key == K_PERIOD:
                        session.photo.adjust_vignette(0.05)
                    else:
                        continue
                    session.hud.photo_lines = session.photo.hud_lines()
                    session.update(px, pz, building_count=building_count, dt=dt)
                elif event.key == K_e and session:
                    new_pos = session.press_interact(px, pz)
                    if new_pos:
                        px, pz = new_pos
                        prev_x, prev_z = px, pz
                        frame_start_x, frame_start_z = px, pz
                elif event.key == K_m and session:
                    session.hud.show_mystery_journal = not session.hud.show_mystery_journal
                    session.update(px, pz, building_count=building_count)
                elif event.key == K_j and session:
                    session.toggle_evolution_journal()
                    session.update(px, pz, building_count=building_count)
                elif event.key == K_y and session:
                    session.hud.dialogue_lines = session.try_accuse_nearest()
                    session.update(px, pz, building_count=building_count)
                elif session and session.in_subway_menu:
                    dest_keys = {K_1: 0, K_2: 1, K_3: 2, K_4: 3, K_5: 4, K_6: 5}
                    if event.key in dest_keys:
                        if session.select_subway_destination(dest_keys[event.key]):
                            px, pz = session.subway_spawn()
                            prev_x, prev_z = px, pz
                            frame_start_x, frame_start_z = px, pz
                        session.update(px, pz, building_count=building_count, dt=dt)
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if session and session.in_twin:
                    session.twin_select_at(px, pz)
                    session.update(px, pz, building_count=building_count, dt=dt)
                else:
                    mouse_look.toggle()
                    _set_mouse_look(mouse_look.active)
            elif event.type == MOUSEWHEEL and session and session.in_photo:
                session.photo.set_time_fraction(session.photo.time_fraction + event.y * 0.02)
                session.hud.photo_lines = session.photo.hud_lines()
                session.update(px, pz, building_count=building_count, dt=dt)
            elif event.type == MOUSEWHEEL and session and session.in_twin:
                session.twin.adjust_zoom(event.y)
                session.update(px, pz, building_count=building_count, dt=dt)
            elif event.type == pygame.VIDEORESIZE:
                width, height = event.size
                screen = pygame.display.set_mode(
                    (width, height), OPENGL | DOUBLEBUF | RESIZABLE
                )
                setup_gl(width, height)

        keys = pygame.key.get_pressed()
        movement = read_movement(keys)
        in_subway = session is not None and session.in_subway
        in_subway_menu = session is not None and session.in_subway_menu
        in_interior = session is not None and session.in_interior
        in_twin = session is not None and session.in_twin
        in_photo = session is not None and session.in_photo
        speed_mult = world_speed_multiplier(movement.sprint)

        twin_time_scale = 1.0
        if session and session.in_twin:
            twin_time_scale = session.twin.time_scale if not session.twin.paused else 0.0

        if stream and not in_interior and not in_subway and not in_subway_menu:
            stream.update(
                dt,
                px,
                pz,
                speed_multiplier=speed_mult if not in_twin and not in_photo else 1.0,
                tick_city=session is None,
            )
            if session and not (in_photo and session.photo.pause_simulation):
                session.simulation.advance_world(
                    dt,
                    speed_multiplier=speed_mult if not in_twin and not in_photo else 1.0,
                    time_scale=twin_time_scale if in_twin else 1.0,
                )

        mx, my = pygame.mouse.get_rel()
        if in_photo and session:
            cam = session.photo.camera
            yaw, pitch = mouse_look.apply(mx, my, cam.yaw, cam.pitch)
            cam.yaw, cam.pitch = yaw, pitch
        else:
            yaw, pitch = mouse_look.apply(mx, my, yaw, pitch)
            move_x, move_z = movement_delta_3d(movement, yaw, dt=dt)
            if (move_x or move_z) and not in_subway and not in_subway_menu and not in_twin:
                new_x = px + move_x
                new_z = pz + move_z
                if (in_interior or in_subway) and session:
                    if in_subway:
                        px, pz = session.subway_spawn()
                    else:
                        px, pz = session.clamp_interior(new_x, new_z)
                else:
                    px, pz = world3d.resolve_move(prev_x, prev_z, new_x, new_z)
                prev_x, prev_z = px, pz
            elif in_subway and session:
                px, pz = session.subway_spawn()

        jump_height = jump.update(dt)
        avatar.update(dt, moving=movement.active and not in_photo, sprinting=movement.sprint)
        ground_y = jump_height
        if in_photo and session:
            cam = session.photo.camera
            vertical = 0.0
            if keys[pygame.K_SPACE]:
                vertical += 1.0
            if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
                vertical -= 1.0
            cam.move(movement.forward, movement.strafe, vertical, dt)
            px, ground_y, pz = cam.x, cam.y, cam.z
        from nyc_world.city.world_clock import WorldClock

        sim_clock = stream.clock if stream else None
        render_clock = sim_clock or WorldClock()
        if session and session.in_photo:
            render_clock = session.photo.visual_clock(render_clock)

        if (in_interior or in_subway) and session and session.current_interior and not in_photo:
            render_interior_frame(
                session.current_interior.build_boxes(),
                px,
                ground_y,
                pz,
                yaw,
                pitch,
                avatar=avatar,
            )
        else:
            render_frame(
                clock=render_clock,
                streets=stream.street_scene if stream else None,
                buildings=stream.render_buildings if stream else world3d.buildings,
                landmarks=stream.render_landmarks if stream else [],
                props=world3d.boxes,
                npcs=stream.render_npcs if stream else [],
                vehicles=stream.render_vehicles if stream else [],
                px=px,
                py=ground_y,
                pz=pz,
                yaw=yaw,
                pitch=pitch,
                avatar=avatar,
                twin=session.twin if session else None,
                photo=session.photo if session else None,
                minds=session.simulation.minds if session else None,
                selected_id=session.twin.selected_id if session and session.in_twin else None,
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
                dt=dt,
            )
            if session._pending_teleport:
                px, pz = session._pending_teleport
                prev_x, prev_z = px, pz
                frame_start_x, frame_start_z = px, pz
                session._pending_teleport = None
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
                minimap_timer += dt
                moved = abs(px - frame_start_x) + abs(pz - frame_start_z)
                if minimap_timer >= minimap_interval or moved > 3.0 or session.hud.minimap is None:
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
                    minimap_timer = 0.0
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
        session.save(px, pz)
        print(f"Saved game to {session.save_path}")
        session.close()
    pygame.quit()


if __name__ == "__main__":
    main()

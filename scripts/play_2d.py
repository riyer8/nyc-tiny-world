#!/usr/bin/env python3
"""Play the 2D top-down map view."""

import sys

import _bootstrap  # noqa: F401
import pygame

from nyc_world.core import World
from nyc_world.game import CONTROLS_HELP, movement_delta_2d, read_movement
from nyc_world.paths import DEFAULT_MAP_PATH

FPS = 60
TILE_SIZE = 16
VIEWPORT_W, VIEWPORT_H = 640, 480
PLAYER_SPEED = 120
PLAYER_RADIUS = 6
PLAYER_COLOR = (50, 50, 50)
HUD_COLOR = (240, 240, 235)
HUD_SHADOW = (20, 20, 25)


def draw_player(surface: pygame.Surface, x: int, y: int, size: int) -> None:
    font_names = ["Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji"]
    for name in font_names:
        try:
            font = pygame.font.SysFont(name, size)
            rendered = font.render("🧍", True, (0, 0, 0))
            if rendered.get_width() > 0:
                surface.blit(rendered, rendered.get_rect(center=(x, y)))
                return
        except Exception:
            continue
    head_r = max(4, size // 4)
    pygame.draw.circle(surface, PLAYER_COLOR, (x, y - head_r * 2), head_r)
    pygame.draw.line(surface, PLAYER_COLOR, (x, y - head_r), (x, y + head_r), 2)
    pygame.draw.line(surface, PLAYER_COLOR, (x - head_r * 2, y), (x + head_r * 2, y), 2)
    pygame.draw.line(surface, PLAYER_COLOR, (x, y + head_r), (x - head_r * 2, y + head_r * 3), 2)
    pygame.draw.line(surface, PLAYER_COLOR, (x, y + head_r), (x + head_r * 2, y + head_r * 3), 2)


def draw_hud(
    surface: pygame.Surface,
    world: World,
    player_x: float,
    player_y: float,
    *,
    sprinting: bool = False,
) -> None:
    font = pygame.font.SysFont("Menlo", 13)
    lines = [f"game  x={player_x:.0f}  y={player_y:.0f}"]
    if sprinting:
        lines.append("mode  SPRINT (Space)")
    if world.projection:
        lat, lon = world.projection.to_gps(player_x, player_y)
        lines.append(f"GPS   {lat:.5f}, {lon:.5f}")
        lines.append(f"area  {world.projection.area_name}")
    y = 8
    for line in lines:
        surface.blit(font.render(line, True, HUD_SHADOW), (9, y + 1))
        surface.blit(font.render(line, True, HUD_COLOR), (8, y))
        y += 18

    help_font = pygame.font.SysFont("Menlo", 11)
    help_surf = help_font.render(CONTROLS_HELP, True, (170, 175, 185))
    surface.blit(help_surf, (8, VIEWPORT_H - 18))


def try_move(world: World, x: float, y: float, dx: float, dy: float) -> tuple[float, float]:
    new_x = x + dx
    if not world.collides(new_x, y, PLAYER_RADIUS):
        x = new_x
    new_y = y + dy
    if not world.collides(x, new_y, PLAYER_RADIUS):
        y = new_y
    return x, y


def main() -> None:
    if not DEFAULT_MAP_PATH.exists():
        print("No map found. Run: python3 scripts/generate_map.py")
        sys.exit(1)

    pygame.init()
    screen = pygame.display.set_mode((VIEWPORT_W, VIEWPORT_H))
    world = World.from_file(DEFAULT_MAP_PATH, tile_size=TILE_SIZE)
    title = "NYC Tiny World"
    if world.projection:
        title += f" — {world.projection.area_name}"
    pygame.display.set_caption(title)
    print(CONTROLS_HELP)

    player_x, player_y = world.player_spawn
    clock = pygame.time.Clock()
    running = True

    while running:
        dt = clock.tick(FPS) / 1000.0
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False

        movement = read_movement(pygame.key.get_pressed())
        dx, dy = movement_delta_2d(movement, PLAYER_SPEED, dt)
        if dx or dy:
            player_x, player_y = try_move(world, player_x, player_y, dx, dy)

        cam_x = max(0, min(max(0, world.width_px - VIEWPORT_W), int(player_x - VIEWPORT_W // 2)))
        cam_y = max(0, min(max(0, world.height_px - VIEWPORT_H), int(player_y - VIEWPORT_H // 2)))

        screen.fill((30, 30, 35))
        world.draw(screen, cam_x, cam_y)
        draw_player(screen, int(player_x - cam_x), int(player_y - cam_y), TILE_SIZE)
        draw_hud(screen, world, player_x, player_y, sprinting=movement.sprint)
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()

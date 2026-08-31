from __future__ import annotations

import pygame

# Tile characters
SIDEWALK = "."
BUILDING = "B"
ROAD = "R"
TREE = "T"
LIGHT = "L"
CAR = "C"
PARK = "G"
POI = "O"
PLAYER_SPAWN = "P"

ALL_TILES = frozenset({SIDEWALK, BUILDING, ROAD, TREE, LIGHT, CAR, PARK, POI})
SOLID_TILES = frozenset({BUILDING, TREE})


class TileSprites:
  def __init__(self, tile_size: int = 32) -> None:
    self.tile_size = tile_size
    self._cache: dict[str, pygame.Surface] = {}

  def get(self, tile: str) -> pygame.Surface:
    if tile not in self._cache:
      surface = pygame.Surface((self.tile_size, self.tile_size))
      drawer = {
        SIDEWALK: self._draw_sidewalk,
        BUILDING: self._draw_building,
        ROAD: self._draw_road,
        TREE: self._draw_tree,
        LIGHT: self._draw_light,
        CAR: self._draw_car,
        PARK: self._draw_park,
        POI: self._draw_poi,
      }.get(tile, self._draw_sidewalk)
      drawer(surface)
      self._cache[tile] = surface
    return self._cache[tile]

  def _draw_sidewalk(self, s: pygame.Surface) -> None:
    s.fill((205, 200, 190))
    for x in range(0, 32, 8):
      for y in range(0, 32, 8):
        shade = (198, 193, 183) if (x + y) % 16 == 0 else (210, 205, 195)
        pygame.draw.rect(s, shade, (x + 1, y + 1, 6, 6))
    pygame.draw.rect(s, (185, 180, 170), (0, 0, 32, 32), 1)

  def _draw_road(self, s: pygame.Surface) -> None:
    s.fill((58, 60, 66))
    for y in (0, 31):
      pygame.draw.line(s, (140, 140, 145), (0, y), (31, y), 1)
    for x in range(2, 32, 10):
      pygame.draw.rect(s, (230, 210, 70), (x, 14, 6, 3))
    for x in range(0, 32, 16):
      pygame.draw.rect(s, (90, 92, 98), (x, 0, 1, 32))

  def _draw_building(self, s: pygame.Surface) -> None:
    s.fill((135, 175, 215))
    # Main tower
    pygame.draw.rect(s, (75, 95, 140), (6, 4, 20, 28))
    pygame.draw.rect(s, (55, 70, 110), (6, 4, 20, 28), 1)
    # Windows
    for row in range(7, 28, 5):
      for col in range(9, 24, 6):
        lit = ((row + col) % 10) < 7
        color = (200, 230, 255) if lit else (45, 55, 80)
        pygame.draw.rect(s, color, (col, row, 4, 3))
    # Roof detail
    pygame.draw.rect(s, (90, 100, 130), (10, 2, 12, 3))
    pygame.draw.rect(s, (110, 115, 125), (15, 0, 2, 4))

  def _draw_tree(self, s: pygame.Surface) -> None:
    s.fill((120, 185, 95))
    # Grass patch
    pygame.draw.rect(s, (95, 160, 75), (0, 24, 32, 8))
    # Trunk
    pygame.draw.rect(s, (110, 75, 45), (14, 20, 4, 10))
    # Canopy layers
    pygame.draw.circle(s, (45, 130, 55), (16, 14), 11)
    pygame.draw.circle(s, (55, 150, 65), (11, 16), 8)
    pygame.draw.circle(s, (55, 150, 65), (21, 16), 8)
    pygame.draw.circle(s, (65, 165, 75), (16, 10), 7)

  def _draw_light(self, s: pygame.Surface) -> None:
    s.fill((205, 200, 190))
    # Pole
    pygame.draw.rect(s, (80, 82, 88), (15, 10, 3, 22))
    # Arm
    pygame.draw.rect(s, (80, 82, 88), (10, 10, 12, 3))
    # Housing
    pygame.draw.rect(s, (50, 52, 58), (6, 4, 10, 14))
    pygame.draw.rect(s, (40, 42, 48), (6, 4, 10, 14), 1)
    # Lights
    pygame.draw.circle(s, (220, 55, 55), (11, 7), 2)
    pygame.draw.circle(s, (230, 200, 55), (11, 11), 2)
    pygame.draw.circle(s, (55, 200, 75), (11, 15), 2)

  def _draw_car(self, s: pygame.Surface) -> None:
    s.fill((58, 60, 66))
    # Body
    pygame.draw.rect(s, (210, 55, 50), (5, 10, 22, 14))
    pygame.draw.rect(s, (180, 40, 38), (5, 10, 22, 14), 1)
    # Cabin / windshield
    pygame.draw.rect(s, (160, 210, 230), (9, 12, 14, 8))
    pygame.draw.rect(s, (130, 180, 200), (9, 12, 14, 8), 1)
    # Wheels
    for wx in (7, 23):
      pygame.draw.rect(s, (30, 30, 35), (wx, 8, 4, 4))
      pygame.draw.rect(s, (30, 30, 35), (wx, 22, 4, 4))
    # Headlights
    pygame.draw.rect(s, (255, 245, 180), (6, 13, 2, 3))
    pygame.draw.rect(s, (255, 245, 180), (24, 13, 2, 3))

  def _draw_park(self, s: pygame.Surface) -> None:
    s.fill((95, 165, 80))
    for x in range(2, 32, 8):
      for y in range(2, 32, 8):
        pygame.draw.circle(s, (105, 175, 90), (x, y), 2)
    pygame.draw.rect(s, (130, 190, 110), (10, 22, 12, 3))
    pygame.draw.rect(s, (130, 190, 110), (22, 8, 3, 10))

  def _draw_poi(self, s: pygame.Surface) -> None:
    s.fill((205, 200, 190))
    pygame.draw.rect(s, (220, 140, 60), (10, 14, 12, 14))
    pygame.draw.polygon(s, (200, 80, 70), [(8, 14), (24, 14), (16, 6)])
    pygame.draw.rect(s, (240, 220, 180), (14, 20, 4, 5))
    pygame.draw.circle(s, (255, 230, 100), (16, 11), 2)

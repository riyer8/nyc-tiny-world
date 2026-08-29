from __future__ import annotations

from pathlib import Path

import pygame

from nyc_world.projection import GeoProjection
from nyc_world.sprites import ALL_TILES, PLAYER_SPAWN, SOLID_TILES, SIDEWALK, TileSprites


class World:
  def __init__(
    self,
    map_text: str,
    tile_size: int = 32,
    projection: GeoProjection | None = None,
  ) -> None:
    self.tile_size = tile_size
    self.tiles: list[list[str]] = []
    self.player_spawn = (0.0, 0.0)
    self.projection = projection
    self.sprites = TileSprites(tile_size)
    self._parse(map_text)

  @classmethod
  def from_file(
    cls,
    path: str | Path,
    tile_size: int = 32,
    *,
    meta_path: str | Path | None = None,
  ) -> World:
    map_path = Path(path)
    if meta_path is None:
      meta_path = map_path.with_name("map_meta.json")

    projection = None
    if Path(meta_path).exists():
      projection = GeoProjection.from_file(meta_path)
      tile_size = projection.tile_size

    return cls(map_path.read_text(), tile_size, projection)

  def _parse(self, map_text: str) -> None:
    for row_idx, line in enumerate(map_text.strip().splitlines()):
      row: list[str] = []
      for col_idx, char in enumerate(line):
        if char == PLAYER_SPAWN:
          self.player_spawn = (
            col_idx * self.tile_size + self.tile_size / 2,
            row_idx * self.tile_size + self.tile_size / 2,
          )
          row.append(SIDEWALK)
        elif char in ALL_TILES:
          row.append(char)
        else:
          row.append(SIDEWALK)
      self.tiles.append(row)

  @property
  def cols(self) -> int:
    return len(self.tiles[0]) if self.tiles else 0

  @property
  def rows(self) -> int:
    return len(self.tiles)

  @property
  def width_px(self) -> int:
    return self.cols * self.tile_size

  @property
  def height_px(self) -> int:
    return self.rows * self.tile_size

  def game_to_gps(self, x: float, y: float) -> tuple[float, float] | None:
    if self.projection is None:
      return None
    return self.projection.to_gps(x, y)

  def gps_to_game(self, lat: float, lon: float) -> tuple[float, float] | None:
    if self.projection is None:
      return None
    return self.projection.to_game(lat, lon)

  def tile_at(self, col: int, row: int) -> str | None:
    if row < 0 or col < 0 or row >= self.rows or col >= self.cols:
      return None
    return self.tiles[row][col]

  def is_solid(self, col: int, row: int) -> bool:
    tile = self.tile_at(col, row)
    return tile in SOLID_TILES

  def collides(self, x: float, y: float, radius: float) -> bool:
    left = int((x - radius) // self.tile_size)
    right = int((x + radius) // self.tile_size)
    top = int((y - radius) // self.tile_size)
    bottom = int((y + radius) // self.tile_size)

    for row in range(top, bottom + 1):
      for col in range(left, right + 1):
        if self.is_solid(col, row):
          return True
    return False

  def draw(
    self,
    surface: pygame.Surface,
    camera_x: int = 0,
    camera_y: int = 0,
  ) -> None:
    ts = self.tile_size
    view_w, view_h = surface.get_size()

    start_col = max(0, camera_x // ts)
    start_row = max(0, camera_y // ts)
    end_col = min(self.cols, (camera_x + view_w) // ts + 1)
    end_row = min(self.rows, (camera_y + view_h) // ts + 1)

    for row_idx in range(start_row, end_row):
      for col_idx in range(start_col, end_col):
        tile = self.tiles[row_idx][col_idx]
        sprite = self.sprites.get(tile)
        surface.blit(
          sprite,
          (col_idx * ts - camera_x, row_idx * ts - camera_y),
        )

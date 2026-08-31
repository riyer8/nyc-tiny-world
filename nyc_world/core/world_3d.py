"""Build a 3D scene from the 2D tile map."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nyc_world.core.sprites import PARK, TREE
from nyc_world.core.world import World

if TYPE_CHECKING:
    from nyc_world.map.buildings import Building3D

EYE_HEIGHT = 1.7
PLAYER_RADIUS = 0.6

GROUND_COLORS = {
    PARK: (0.38, 0.62, 0.34),
}


@dataclass(frozen=True)
class Box3D:
    """Axis-aligned box: center position + full width/height/depth."""

    x: float
    y: float
    z: float
    sx: float
    sy: float
    sz: float
    r: float
    g: float
    b: float


class World3D:
    """Turn a tile map into 3D geometry + grid collision."""

    def __init__(self, world: World) -> None:
        from nyc_world.map.buildings import load_buildings_for_area

        self.world = world
        if world.projection:
            self.meters_per_tile = world.projection.meters_per_tile()
        else:
            self.meters_per_tile = 12.5

        self.width_m = world.cols * self.meters_per_tile
        self.depth_m = world.rows * self.meters_per_tile
        self.spawn = self.game_to_world(*world.player_spawn)
        self.buildings: list[Building3D] = []
        if world.projection:
            self.buildings = load_buildings_for_area(world.projection)
        self.boxes: list[Box3D] = self.build_scene()

    def game_to_world(self, game_x: float, game_y: float) -> tuple[float, float, float]:
        """2D map pixels → 3D world (x=east, z=north, y=up)."""
        ts = self.world.tile_size
        x = game_x / ts * self.meters_per_tile
        row = game_y / ts
        z = (self.world.rows - row) * self.meters_per_tile
        return x, EYE_HEIGHT, z

    def tile_center(self, col: int, row: int) -> tuple[float, float]:
        x = (col + 0.5) * self.meters_per_tile
        z = (self.world.rows - row - 0.5) * self.meters_per_tile
        return x, z

    def is_blocked(self, x: float, z: float, radius: float = PLAYER_RADIUS) -> bool:
        ts = self.world.tile_size
        game_x = x / self.meters_per_tile * ts
        game_y = (self.world.rows - z / self.meters_per_tile) * ts

        checks = [
            (game_x, game_y),
            (game_x + radius * ts / self.meters_per_tile, game_y),
            (game_x - radius * ts / self.meters_per_tile, game_y),
            (game_x, game_y + radius * ts / self.meters_per_tile),
            (game_x, game_y - radius * ts / self.meters_per_tile),
        ]
        for gx, gy in checks:
            if self.world.collides(gx, gy, ts * 0.25):
                return True
        return False

    def resolve_move(
        self,
        old_x: float,
        old_z: float,
        new_x: float,
        new_z: float,
    ) -> tuple[float, float]:
        x, z = new_x, new_z
        if self.is_blocked(x, z):
            x, z = old_x, new_z
            if self.is_blocked(x, z):
                x, z = new_x, old_z
                if self.is_blocked(x, z):
                    x, z = old_x, old_z
        return x, z

    def _add_box(
        self,
        boxes: list[Box3D],
        x: float,
        y: float,
        z: float,
        sx: float,
        sy: float,
        sz: float,
        color: tuple[float, float, float],
    ) -> None:
        r, g, b = color
        boxes.append(Box3D(x, y, z, sx, sy, sz, r, g, b))

    def build_scene(self) -> list[Box3D]:
        boxes: list[Box3D] = []
        mpt = self.meters_per_tile

        self._add_box(
            boxes,
            self.width_m / 2,
            -0.05,
            self.depth_m / 2,
            self.width_m,
            0.1,
            self.depth_m,
            (0.76, 0.74, 0.70),
        )

        for row in range(self.world.rows):
            for col in range(self.world.cols):
                tile = self.world.tile_at(col, row)
                if tile is None:
                    continue

                x, z = self.tile_center(col, row)

                if tile == PARK:
                    self._add_box(
                        boxes, x, 0.06, z, mpt * 0.98, 0.12, mpt * 0.98, GROUND_COLORS[PARK]
                    )

                elif tile == TREE:
                    self._add_box(
                        boxes, x, mpt * 0.25, z, mpt * 0.18, mpt * 0.5, mpt * 0.18, (0.45, 0.29, 0.18)
                    )
                    self._add_box(
                        boxes, x, mpt * 0.65, z, mpt * 0.55, mpt * 0.55, mpt * 0.55, (0.22, 0.55, 0.25)
                    )

        return boxes

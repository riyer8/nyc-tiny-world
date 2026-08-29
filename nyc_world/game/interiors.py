"""Simple interior scenes for enterable buildings."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.game.interactables import Interactable, InteractableKind
from nyc_world.core.world_3d import Box3D


@dataclass
class Interior:
    id: str
    name: str
    width: float = 12.0
    depth: float = 10.0
    wall_height: float = 3.5
    floor_color: tuple[float, float, float] = (0.55, 0.50, 0.45)
    interactables: list[Interactable] = field(default_factory=list)

    def build_boxes(self) -> list[Box3D]:
        w, d, h = self.width, self.depth, self.wall_height
        boxes: list[Box3D] = []
        fr, fg, fb = self.floor_color

        boxes.append(Box3D(w / 2, -0.05, d / 2, w, 0.1, d, fr, fg, fb))
        boxes.append(Box3D(w / 2, h / 2, 0.1, w, h, 0.2, 0.4, 0.38, 0.35))
        boxes.append(Box3D(w / 2, h / 2, d - 0.1, w, h, 0.2, 0.4, 0.38, 0.35))
        boxes.append(Box3D(0.1, h / 2, d / 2, 0.2, h, d, 0.4, 0.38, 0.35))
        boxes.append(Box3D(w - 0.1, h / 2, d / 2, 0.2, h, d, 0.4, 0.38, 0.35))

        if self.id == "cafe_interior":
            boxes.append(Box3D(3, 1.1, 2, 4, 2.2, 1.2, 0.45, 0.28, 0.18))
            boxes.append(Box3D(8, 0.5, 7, 2, 1, 2, 0.6, 0.4, 0.25))
        elif self.id == "library_interior":
            boxes.append(Box3D(2, 1.2, 3, 3, 2.4, 5, 0.35, 0.25, 0.15))
            boxes.append(Box3D(8, 1.0, 7, 2.5, 2, 1, 0.3, 0.22, 0.12))
            boxes.append(Box3D(6, 0.8, 5, 1.5, 1.6, 3, 0.32, 0.24, 0.14))
        elif self.id == "photo_shop_interior":
            boxes.append(Box3D(5, 1.0, 4, 6, 2, 2, 0.5, 0.5, 0.55))

        return boxes


INTERIORS: dict[str, Interior] = {
    "cafe_interior": Interior(
        id="cafe_interior",
        name="Village Cafe",
        interactables=[
            Interactable(
                id="exit_cafe",
                kind=InteractableKind.BUILDING,
                x=6,
                z=9,
                label="Exit",
                radius=2.0,
                emoji="🚪",
            ),
        ],
    ),
    "library_interior": Interior(
        id="library_interior",
        name="Jefferson Market Library",
        floor_color=(0.48, 0.44, 0.40),
        interactables=[
            Interactable(
                id="exit_library",
                kind=InteractableKind.BUILDING,
                x=6,
                z=9,
                label="Exit",
                radius=2.0,
                emoji="🚪",
            ),
            Interactable(
                id="camera_clue",
                kind=InteractableKind.OBJECT,
                x=8,
                z=5,
                label="Camera",
                radius=2.5,
                item_id="camera",
                dialogue_id="found_camera",
                emoji="📷",
            ),
        ],
    ),
    "photo_shop_interior": Interior(
        id="photo_shop_interior",
        name="Photo Shop",
        interactables=[
            Interactable(
                id="exit_photo_shop",
                kind=InteractableKind.BUILDING,
                x=6,
                z=9,
                label="Exit",
                radius=2.0,
                emoji="🚪",
            ),
        ],
    ),
}


def get_interior(interior_id: str) -> Interior | None:
    return INTERIORS.get(interior_id)

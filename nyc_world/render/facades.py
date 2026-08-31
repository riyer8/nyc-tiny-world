"""Facade photo textures — cached Wikimedia images mapped to OSM buildings."""

from __future__ import annotations

import json
from pathlib import Path

from nyc_world.paths import FACADES_DIR

# Only project photos when the player is close enough to read them.
FACADE_TEXTURE_RANGE_M = 85.0
_MAX_TEXTURE_CACHE = 128


class FacadeCache:
    """Load and cache facade images from data/facades/."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or FACADES_DIR
        self.manifest: dict[str, str] = {}
        self._textures: dict[str, int] = {}
        self._order: list[str] = []
        manifest_path = self.root / "manifest.json"
        if manifest_path.exists():
            self.manifest = json.loads(manifest_path.read_text())

    def has(self, facade_key: str) -> bool:
        if not facade_key:
            return False
        rel = self.manifest.get(facade_key)
        return bool(rel and (self.root / rel).exists())

    def texture_id(self, facade_key: str) -> int | None:
        if not self.has(facade_key):
            return None
        cached = self._textures.get(facade_key)
        if cached is not None:
            return cached
        rel = self.manifest[facade_key]
        tex_id = _load_image_texture(self.root / rel)
        self._textures[facade_key] = tex_id
        self._order.append(facade_key)
        while len(self._order) > _MAX_TEXTURE_CACHE:
            old = self._order.pop(0)
            old_id = self._textures.pop(old, None)
            if old_id is not None:
                from OpenGL.GL import glDeleteTextures

                glDeleteTextures(1, [old_id])
        return tex_id


_cache: FacadeCache | None = None


def get_facade_cache() -> FacadeCache:
    global _cache
    if _cache is None:
        _cache = FacadeCache()
    return _cache


def reset_facade_cache() -> None:
    """Clear singleton (tests)."""
    global _cache
    _cache = None


def _load_image_texture(path: Path) -> int:
    import pygame
    from OpenGL.GL import (
        GL_RGBA,
        GL_TEXTURE_2D,
        GL_UNSIGNED_BYTE,
        glBindTexture,
        glGenTextures,
        glTexImage2D,
        glTexParameteri,
    )

    surface = pygame.image.load(str(path)).convert_alpha()
    w, h = surface.get_size()
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, 0x2801, 0x2601)  # GL_LINEAR
    glTexParameteri(GL_TEXTURE_2D, 0x2800, 0x2601)
    data = pygame.image.tostring(surface, "RGBA", True)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex_id


def best_wall_index(
    footprint: tuple[tuple[float, float], ...],
    player_x: float,
    player_z: float,
) -> int | None:
    """Wall segment whose outward normal most faces the player."""
    if len(footprint) < 3:
        return None
    best_i = 0
    best_score = float("-inf")
    for i in range(len(footprint)):
        x0, z0 = footprint[i]
        x1, z1 = footprint[(i + 1) % len(footprint)]
        dx, dz = x1 - x0, z1 - z0
        length = (dx * dx + dz * dz) ** 0.5
        if length < 0.5:
            continue
        nx, nz = dz / length, -dx / length  # outward normal for CCW footprint
        mx, mz = (x0 + x1) * 0.5, (z0 + z1) * 0.5
        to_player_x, to_player_z = player_x - mx, player_z - mz
        score = nx * to_player_x + nz * to_player_z
        if score > best_score:
            best_score = score
            best_i = i
    return best_i if best_score > 0 else None


def draw_textured_wall(
    x0: float,
    z0: float,
    x1: float,
    z1: float,
    height: float,
    tex_id: int,
    *,
    brightness: float = 1.0,
    margin: float = 0.08,
) -> None:
    """Project a facade photo onto a wall quad."""
    from OpenGL.GL import (
        GL_BLEND,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_QUADS,
        GL_SRC_ALPHA,
        GL_TEXTURE_2D,
        glBegin,
        glBindTexture,
        glBlendFunc,
        glColor3f,
        glDisable,
        glEnable,
        glEnd,
        glTexCoord2f,
        glVertex3f,
    )

    y0 = margin
    y1 = max(y0 + 1.0, height - margin)
    glEnable(GL_TEXTURE_2D)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    b = max(0.35, min(1.2, brightness))
    glColor3f(b, b, b)
    glBegin(GL_QUADS)
    glTexCoord2f(0.0, 1.0)
    glVertex3f(x0, y0, z0)
    glTexCoord2f(1.0, 1.0)
    glVertex3f(x1, y0, z1)
    glTexCoord2f(1.0, 0.0)
    glVertex3f(x1, y1, z1)
    glTexCoord2f(0.0, 0.0)
    glVertex3f(x0, y1, z0)
    glEnd()
    glDisable(GL_BLEND)
    glDisable(GL_TEXTURE_2D)

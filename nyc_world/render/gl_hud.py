"""OpenGL HUD overlay for prompts, dialogue, and quest status."""

from __future__ import annotations

from nyc_world.game.game_session import HudState

_font_cache: dict[int, object] = {}
_initialized = False


def _ensure_font(size: int = 20):
    import pygame

    global _initialized
    if not _initialized:
        if not pygame.font.get_init():
            pygame.font.init()
        _initialized = True
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont("menlo,monaco,consolas,courier new", size)
    return _font_cache[size]


def _surface_to_texture(surface) -> tuple[int, int, int]:
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

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, 0x2801, 0x2601)
    glTexParameteri(GL_TEXTURE_2D, 0x2800, 0x2601)
    w, h = surface.get_size()
    data = pygame.image.tostring(surface, "RGBA", True)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex_id, w, h


def _draw_surface(x: int, y: int, surface, screen_h: int) -> None:
    import pygame
    from OpenGL.GL import (
        GL_BLEND,
        GL_ONE_MINUS_SRC_ALPHA,
        GL_SRC_ALPHA,
        GL_TEXTURE_2D,
        GL_QUADS,
        glBegin,
        glBindTexture,
        glBlendFunc,
        glColor4f,
        glDisable,
        glEnable,
        glEnd,
        glTexCoord2f,
        glVertex2f,
    )

    tex_id, w, h = _surface_to_texture(surface)
    gl_y = screen_h - y - h
    glEnable(GL_TEXTURE_2D)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glColor4f(1, 1, 1, 1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glBegin(GL_QUADS)
    glTexCoord2f(0, 1)
    glVertex2f(x, gl_y)
    glTexCoord2f(1, 1)
    glVertex2f(x + w, gl_y)
    glTexCoord2f(1, 0)
    glVertex2f(x + w, gl_y + h)
    glTexCoord2f(0, 0)
    glVertex2f(x, gl_y + h)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)


def _render_lines(lines: list[str], size: int = 20, color=(240, 240, 240), bg=(0, 0, 0, 180)):
    import pygame

    font = _ensure_font(size)
    rendered = [font.render(line, True, color) for line in lines]
    w = max(r.get_width() for r in rendered) + 24
    h = sum(r.get_height() for r in rendered) + 20
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    surf.fill(bg)
    y = 10
    for r in rendered:
        surf.blit(r, (12, y))
        y += r.get_height()
    return surf


def draw_hud(width: int, height: int, hud: HudState) -> None:
    """Draw 2D overlay on top of the 3D scene."""
    import pygame
    from OpenGL.GL import (
        GL_BLEND,
        GL_DEPTH_TEST,
        GL_PROJECTION,
        GL_MODELVIEW,
        glDisable,
        glEnable,
        glLoadIdentity,
        glMatrixMode,
        glOrtho,
        glPopMatrix,
        glPushMatrix,
    )

    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    glOrtho(0, width, 0, height, -1, 1)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glDisable(GL_DEPTH_TEST)

    if hud.quest_text:
        surf = _render_lines([hud.quest_text], size=18, color=(255, 220, 120))
        _draw_surface(12, 12, surf, height)

    if hud.inventory:
        inv_lines = ["Inventory:"] + [f"  • {item}" for item in hud.inventory]
        surf = _render_lines(inv_lines, size=16, color=(200, 230, 255))
        _draw_surface(width - surf.get_width() - 12, 12, surf, height)

    if hud.prompt:
        prompt_lines = hud.prompt.split("\n")
        surf = _render_lines(prompt_lines, size=22, color=(255, 255, 255), bg=(0, 0, 0, 200))
        cx = (width - surf.get_width()) // 2
        cy = height // 2 + 40
        _draw_surface(cx, cy, surf, height)

    if hud.dialogue_lines:
        surf = _render_lines(hud.dialogue_lines, size=18, color=(230, 230, 230))
        _draw_surface(12, height - surf.get_height() - 24, surf, height)
    elif hud.controls_hint:
        hint = hud.controls_hint
        if hud.sprinting:
            hint = "SPRINT  ·  " + hint
        surf = _render_lines([hint], size=14, color=(180, 190, 200), bg=(0, 0, 0, 140))
        _draw_surface(12, height - surf.get_height() - 12, surf, height)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

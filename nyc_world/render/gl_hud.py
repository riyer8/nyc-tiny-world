"""OpenGL HUD — crisp layout with no overlapping panels."""

from __future__ import annotations

from dataclasses import dataclass

from nyc_world.game.game_session import HudState

# Render text/panels at 2× for sharp labels on retina displays.
HUD_SCALE = 2
MARGIN = 14
GAP = 10

_font_cache: dict[tuple[int, bool], object] = {}
_initialized = False


def _ensure_font(size: int = 20, bold: bool = False):
    import pygame

    global _initialized
    if not pygame.font.get_init():
        pygame.font.init()
    _initialized = True
    key = (size, bold)
    if key not in _font_cache:
        names = "sf pro display,helvetica neue,avenir next,menlo,monaco,arial"
        _font_cache[key] = pygame.font.SysFont(names, size, bold=bold)
    return _font_cache[key]


def _scale_surface(surf):
    import pygame

    w, h = surf.get_size()
    if HUD_SCALE == 1:
        return surf
    return pygame.transform.smoothscale(surf, (w // HUD_SCALE, h // HUD_SCALE))


def _panel_surface(
    lines: list[str],
    *,
    title: str | None = None,
    size: int = 15,
    color: tuple[int, int, int] = (220, 228, 240),
    title_color: tuple[int, int, int] = (140, 180, 255),
    bg: tuple[int, int, int, int] = (12, 16, 28, 230),
    border: tuple[int, int, int] = (55, 70, 100),
    pad_x: int = 16,
    pad_y: int = 14,
    min_width: int = 0,
) -> "pygame.Surface":
    import pygame

    font = _ensure_font(size * HUD_SCALE)
    title_font = _ensure_font((size + 1) * HUD_SCALE, bold=True)
    rendered = [font.render(line, True, color) for line in lines]
    text_w = max((r.get_width() for r in rendered), default=0)
    if title:
        text_w = max(text_w, title_font.size(title)[0])
    w = max(min_width * HUD_SCALE, text_w + pad_x * 2 * HUD_SCALE)
    line_h = font.get_linesize()
    title_h = title_font.get_linesize() + 6 * HUD_SCALE if title else 0
    h = pad_y * 2 * HUD_SCALE + title_h + len(rendered) * line_h
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(surf, bg, surf.get_rect(), border_radius=10 * HUD_SCALE)
    pygame.draw.rect(surf, border, surf.get_rect(), 2, border_radius=10 * HUD_SCALE)
    y = pad_y * HUD_SCALE
    if title:
        surf.blit(title_font.render(title, True, title_color), (pad_x * HUD_SCALE, y))
        y += title_h
        pygame.draw.line(
            surf,
            (border[0], border[1], border[2], 120),
            (pad_x * HUD_SCALE, y - 4 * HUD_SCALE),
            (w - pad_x * HUD_SCALE, y - 4 * HUD_SCALE),
            1,
        )
    for r in rendered:
        surf.blit(r, (pad_x * HUD_SCALE, y))
        y += line_h
    return _scale_surface(surf)


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
    glTexParameteri(GL_TEXTURE_2D, 0x2801, 0x2601)  # LINEAR
    glTexParameteri(GL_TEXTURE_2D, 0x2800, 0x2601)
    w, h = surface.get_size()
    data = pygame.image.tostring(surface, "RGBA", True)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)
    return tex_id, w, h


def _draw_surface(x: int, y: int, surface, screen_h: int) -> tuple[int, int]:
    """Draw surface at top-left (x, y). Returns (width, height)."""
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
    glTexCoord2f(0, 0)
    glVertex2f(x, gl_y)
    glTexCoord2f(1, 0)
    glVertex2f(x + w, gl_y)
    glTexCoord2f(1, 1)
    glVertex2f(x + w, gl_y + h)
    glTexCoord2f(0, 1)
    glVertex2f(x, gl_y + h)
    glEnd()
    glDisable(GL_TEXTURE_2D)
    glDisable(GL_BLEND)
    return w, h


@dataclass
class _Layout:
    width: int
    height: int
    left_y: int = MARGIN
    right_y: int = MARGIN
    right_x: int = 0

    def __post_init__(self) -> None:
        self.right_x = self.width - MARGIN

    def place_left(self, surf, screen_h: int) -> None:
        w, h = _draw_surface(MARGIN, self.left_y, surf, screen_h)
        self.left_y += h + GAP

    def place_right(self, surf, screen_h: int) -> None:
        w, h = surf.get_size()
        x = self.right_x - w
        _draw_surface(x, self.right_y, surf, screen_h)
        self.right_y += h + GAP


def draw_hud(width: int, height: int, hud: HudState) -> None:
    """Draw a clean, non-overlapping HUD overlay."""
    import pygame
    from OpenGL.GL import (
        GL_DEPTH_TEST,
        GL_MODELVIEW,
        GL_PROJECTION,
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

    layout = _Layout(width, height)

    # --- Left column: quest → debug (optional) ---
    if hud.quest_text:
        layout.place_left(
            _panel_surface(
                [hud.quest_text],
                title="QUEST",
                size=16,
                color=(255, 224, 140),
                title_color=(255, 200, 80),
                bg=(28, 22, 10, 235),
                border=(120, 90, 40),
            ),
            height,
        )

    if hud.show_geo_debug:
        debug_lines = [
            f"{hud.player_lat:.5f}, {hud.player_lon:.5f}",
            f"Street  {hud.nearest_street or '—'}",
            f"POI     {hud.nearest_poi or '—'}",
            f"Area    {hud.neighborhood or '—'}",
            f"Tiles   {hud.streaming_tiles}  ·  3D {hud.streaming_buildings}",
        ]
        sim_lines = list(getattr(hud, "simulation_lines", []) or [])
        if sim_lines:
            debug_lines.append("")
            debug_lines.extend(sim_lines)
        debug_lines.append("Press G to hide")
        layout.place_left(
            _panel_surface(
                debug_lines,
                title="LOCATION & SIM",
                size=13,
                color=(175, 210, 245),
                min_width=240,
            ),
            height,
        )

    # --- Right column: minimap → profile → living city ---
    if hud.minimap is not None:
        layout.place_right(hud.minimap.surface, height)

    if hud.profile_lines:
        layout.place_right(
            _panel_surface(
                hud.profile_lines,
                title="PLAYER",
                size=14,
                color=(205, 225, 255),
                min_width=hud.minimap.width if hud.minimap else 220,
            ),
            height,
        )

    mind_lines = getattr(hud, "npc_mind_lines", None) or []
    if mind_lines:
        layout.place_right(
            _panel_surface(
                mind_lines,
                title="LIVING CITY",
                size=13,
                color=(255, 205, 220),
                title_color=(255, 140, 170),
                bg=(32, 14, 24, 235),
                border=(110, 55, 80),
                min_width=hud.minimap.width if hud.minimap else 220,
            ),
            height,
        )

    # --- Center-bottom: interaction prompt ---
    if hud.prompt:
        prompt_lines = hud.prompt.split("\n")
        surf = _panel_surface(
            prompt_lines,
            title="INTERACT",
            size=17,
            color=(255, 255, 255),
            bg=(0, 0, 0, 210),
            border=(90, 90, 110),
            min_width=320,
        )
        cx = (width - surf.get_width()) // 2
        cy = height // 2 + 50
        _draw_surface(cx, cy, surf, height)

    # --- Bottom: dialogue or controls ---
    if hud.dialogue_lines:
        surf = _panel_surface(
            hud.dialogue_lines,
            title="DIALOGUE",
            size=15,
            color=(235, 235, 240),
            min_width=min(width - 2 * MARGIN, 700),
        )
        _draw_surface(MARGIN, height - surf.get_height() - MARGIN, surf, height)
    elif hud.controls_hint:
        hint = hud.controls_hint
        if hud.adjusting_view:
            hint = "Adjusting view — click to lock  ·  " + hint
        else:
            hint = "Click to adjust view  ·  " + hint
        if hud.sprinting:
            hint = "SPRINT  ·  " + hint
        surf = _panel_surface([hint], size=12, color=(165, 175, 190), bg=(0, 0, 0, 150), border=(50, 55, 65))
        _draw_surface(MARGIN, height - surf.get_height() - MARGIN, surf, height)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

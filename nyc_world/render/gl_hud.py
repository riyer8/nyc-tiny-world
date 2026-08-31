"""OpenGL HUD — cached textures, no per-frame glGenTextures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nyc_world.game.game_session import HudState

HUD_SCALE = 2
MARGIN = 14
GAP = 10
_MAX_TEXTURE_CACHE = 48

_font_cache: dict[tuple[int, bool], object] = {}
_panel_cache: dict[str, object] = {}
_texture_cache: dict[str, tuple[int, int, int]] = {}  # key -> (tex_id, w, h)
_texture_order: list[str] = []


def _ensure_font(size: int = 20, bold: bool = False):
    import pygame

    if not pygame.font.get_init():
        pygame.font.init()
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
    cache_key: str | None = None,
    title: str | None = None,
    size: int = 15,
    color: tuple[int, int, int] = (220, 228, 240),
    title_color: tuple[int, int, int] = (140, 180, 255),
    bg: tuple[int, int, int, int] = (12, 16, 28, 230),
    border: tuple[int, int, int] = (55, 70, 100),
    pad_x: int = 16,
    pad_y: int = 14,
    min_width: int = 0,
):
    import pygame

    if cache_key and cache_key in _panel_cache:
        return _panel_cache[cache_key]

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
    for r in rendered:
        surf.blit(r, (pad_x * HUD_SCALE, y))
        y += line_h
    result = _scale_surface(surf)
    if cache_key:
        if len(_panel_cache) > 64:
            _panel_cache.clear()
        _panel_cache[cache_key] = result
    return result


def _texture_for_surface(surface, cache_key: str) -> tuple[int, int, int]:
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

    w, h = surface.get_size()
    cached = _texture_cache.get(cache_key)
    if cached and cached[1] == w and cached[2] == h:
        return cached

    if cached:
        from OpenGL.GL import glDeleteTextures

        glDeleteTextures(1, [cached[0]])

    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexParameteri(GL_TEXTURE_2D, 0x2801, 0x2601)
    glTexParameteri(GL_TEXTURE_2D, 0x2800, 0x2601)
    data = pygame.image.tostring(surface, "RGBA", True)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, w, h, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

    _texture_cache[cache_key] = (tex_id, w, h)
    if cache_key in _texture_order:
        _texture_order.remove(cache_key)
    _texture_order.append(cache_key)
    while len(_texture_order) > _MAX_TEXTURE_CACHE:
        old = _texture_order.pop(0)
        old_tex = _texture_cache.pop(old, None)
        if old_tex:
            from OpenGL.GL import glDeleteTextures

            glDeleteTextures(1, [old_tex[0]])

    return tex_id, w, h


def _draw_surface(x: int, y: int, surface, screen_h: int, *, cache_key: str) -> tuple[int, int]:
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

    tex_id, w, h = _texture_for_surface(surface, cache_key)
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

    def place_left(self, surf, screen_h: int, cache_key: str) -> None:
        w, h = _draw_surface(MARGIN, self.left_y, surf, screen_h, cache_key=cache_key)
        self.left_y += h + GAP

    def place_right(self, surf, screen_h: int, cache_key: str) -> None:
        w, h = surf.get_size()
        x = self.right_x - w
        _draw_surface(x, self.right_y, surf, screen_h, cache_key=cache_key)
        self.right_y += h + GAP


def draw_hud(width: int, height: int, hud: HudState) -> None:
    """Draw HUD overlay with cached GPU textures."""
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

    if getattr(hud, "hide_hud", False):
        photo_lines = getattr(hud, "photo_lines", None) or []
        if photo_lines:
            photo_key = "photo:" + "|".join(photo_lines)
            surf = _panel_surface(
                photo_lines,
                cache_key=photo_key,
                title="PHOTO",
                size=13,
                color=(240, 245, 255),
                title_color=(180, 210, 255),
                bg=(8, 12, 20, 200),
                border=(60, 80, 110),
                min_width=360,
            )
            cx = (width - surf.get_width()) // 2
            _draw_surface(cx, 24, surf, height, cache_key=photo_key)
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glEnable(GL_DEPTH_TEST)
        return

    feed_lines = getattr(hud, "feed_banner_lines", None) or []
    if feed_lines:
        feed_key = "feed:" + "|".join(feed_lines)
        feed_surf = _panel_surface(
            feed_lines,
            cache_key=feed_key,
            size=13,
            color=(220, 235, 255),
            bg=(10, 18, 32, 220),
            border=(60, 90, 140),
            min_width=min(width - 2 * MARGIN, 720),
        )
        _draw_surface((width - feed_surf.get_width()) // 2, height - feed_surf.get_height() - MARGIN, feed_surf, height, cache_key=feed_key)

    if hud.quest_text:
        layout.place_left(
            _panel_surface(
                [hud.quest_text],
                cache_key=f"quest:{hud.quest_text}",
                title="QUEST",
                size=16,
                color=(255, 224, 140),
                title_color=(255, 200, 80),
                bg=(28, 22, 10, 235),
                border=(120, 90, 40),
            ),
            height,
            cache_key=f"quest:{hud.quest_text}",
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
        dbg_key = "debug:" + "|".join(debug_lines)
        layout.place_left(
            _panel_surface(
                debug_lines,
                cache_key=dbg_key,
                title="LOCATION & SIM",
                size=13,
                color=(175, 210, 245),
                min_width=240,
            ),
            height,
            cache_key=dbg_key,
        )

    if hud.minimap is not None:
        mm_key = f"minimap:{id(hud.minimap.surface)}"
        layout.place_right(hud.minimap.surface, height, cache_key=mm_key)

    if hud.profile_lines:
        prof_key = "prof:" + "|".join(hud.profile_lines)
        layout.place_right(
            _panel_surface(
                hud.profile_lines,
                cache_key=prof_key,
                title="PLAYER",
                size=14,
                color=(205, 225, 255),
                min_width=hud.minimap.width if hud.minimap else 220,
            ),
            height,
            cache_key=prof_key,
        )

    mind_lines = getattr(hud, "npc_mind_lines", None) or []
    if mind_lines:
        mind_key = "mind:" + "|".join(mind_lines)
        layout.place_right(
            _panel_surface(
                mind_lines,
                cache_key=mind_key,
                title="LIVING CITY",
                size=13,
                color=(255, 205, 220),
                title_color=(255, 140, 170),
                bg=(32, 14, 24, 235),
                border=(110, 55, 80),
                min_width=hud.minimap.width if hud.minimap else 220,
            ),
            height,
            cache_key=mind_key,
        )

    memory_lines = getattr(hud, "npc_memory_lines", None) or []
    memory_title = getattr(hud, "npc_memory_title", None)
    if memory_lines and memory_title:
        mem_key = "mem:" + memory_title + "|" + "|".join(memory_lines)
        layout.place_left(
            _panel_surface(
                memory_lines,
                cache_key=mem_key,
                title=memory_title,
                size=13,
                color=(240, 235, 225),
                title_color=(255, 180, 120),
                bg=(24, 20, 18, 235),
                border=(90, 75, 60),
                min_width=280,
            ),
            height,
            cache_key=mem_key,
        )

    mystery_lines = getattr(hud, "mystery_lines", None) or []
    if mystery_lines and getattr(hud, "show_mystery_journal", False):
        mystery_key = "mystery:" + "|".join(mystery_lines)
        layout.place_left(
            _panel_surface(
                mystery_lines,
                cache_key=mystery_key,
                title="MYSTERY",
                size=13,
                color=(210, 200, 255),
                title_color=(180, 150, 255),
                bg=(18, 14, 32, 235),
                border=(80, 60, 120),
                min_width=300,
            ),
            height,
            cache_key=mystery_key,
        )

    subway_lines = getattr(hud, "subway_lines", None) or []
    if subway_lines:
        subway_key = "subway:" + "|".join(subway_lines)
        layout.place_left(
            _panel_surface(
                subway_lines,
                cache_key=subway_key,
                title="SUBWAY",
                size=14,
                color=(200, 230, 255),
                title_color=(100, 180, 255),
                bg=(8, 20, 32, 235),
                border=(40, 90, 140),
                min_width=340,
            ),
            height,
            cache_key=subway_key,
        )

    twin_lines = getattr(hud, "twin_lines", None) or []
    if twin_lines:
        twin_key = "twin:" + "|".join(twin_lines)
        layout.place_right(
            _panel_surface(
                twin_lines,
                cache_key=twin_key,
                title="DIGITAL TWIN",
                size=14,
                color=(210, 240, 220),
                title_color=(120, 220, 160),
                bg=(10, 24, 16, 235),
                border=(50, 110, 70),
                min_width=360,
            ),
            height,
            cache_key=twin_key,
        )

    twin_inspector = getattr(hud, "twin_inspector_lines", None) or []
    if twin_inspector:
        insp_key = "twininsp:" + "|".join(twin_inspector)
        layout.place_left(
            _panel_surface(
                twin_inspector,
                cache_key=insp_key,
                title="INSPECT",
                size=13,
                color=(235, 245, 235),
                title_color=(160, 230, 180),
                bg=(14, 22, 16, 235),
                border=(60, 100, 70),
                min_width=300,
            ),
            height,
            cache_key=insp_key,
        )

    imagine_lines = getattr(hud, "imagine_lines", None) or []
    if imagine_lines:
        img_key = "imagine:" + "|".join(imagine_lines)
        surf = _panel_surface(
            imagine_lines,
            cache_key=img_key,
            title="IMAGINE",
            size=13,
            color=(230, 220, 255),
            title_color=(180, 150, 255),
            bg=(16, 12, 28, 235),
            border=(80, 60, 120),
            min_width=min(width - 2 * MARGIN, 680),
        )
        cx = (width - surf.get_width()) // 2
        _draw_surface(cx, height // 2 - surf.get_height() // 2, surf, height, cache_key=img_key)

    god_lines = getattr(hud, "god_lines", None) or []
    if god_lines:
        god_key = "god:" + "|".join(god_lines)
        layout.place_left(
            _panel_surface(
                god_lines,
                cache_key=god_key,
                title="CITY LAB",
                size=13,
                color=(255, 240, 200),
                title_color=(255, 200, 80),
                bg=(28, 20, 8, 235),
                border=(120, 90, 40),
                min_width=360,
            ),
            height,
            cache_key=god_key,
        )

    evolution_lines = getattr(hud, "evolution_lines", None) or []
    if evolution_lines:
        evo_key = "evo:" + "|".join(evolution_lines)
        layout.place_right(
            _panel_surface(
                evolution_lines,
                cache_key=evo_key,
                title="EVOLUTION",
                size=13,
                color=(220, 235, 255),
                title_color=(140, 190, 255),
                bg=(10, 16, 28, 235),
                border=(50, 80, 120),
                min_width=380,
            ),
            height,
            cache_key=evo_key,
        )

    if hud.prompt:
        prompt_key = "prompt:" + hud.prompt
        surf = _panel_surface(
            hud.prompt.split("\n"),
            cache_key=prompt_key,
            title="INTERACT",
            size=17,
            color=(255, 255, 255),
            bg=(0, 0, 0, 210),
            border=(90, 90, 110),
            min_width=320,
        )
        cx = (width - surf.get_width()) // 2
        _draw_surface(cx, height // 2 + 50, surf, height, cache_key=prompt_key)

    if hud.dialogue_lines:
        dlg_key = "dlg:" + "|".join(hud.dialogue_lines)
        surf = _panel_surface(
            hud.dialogue_lines,
            cache_key=dlg_key,
            title="DIALOGUE",
            size=15,
            color=(235, 235, 240),
            min_width=min(width - 2 * MARGIN, 700),
        )
        _draw_surface(MARGIN, height - surf.get_height() - MARGIN, surf, height, cache_key=dlg_key)
    elif hud.controls_hint:
        hint = hud.controls_hint
        if hud.adjusting_view:
            hint = "Adjusting view — click to lock  ·  " + hint
        else:
            hint = "Click to adjust view  ·  " + hint
        if hud.sprinting:
            hint = "SPRINT  ·  " + hint
        hint_key = "hint:" + hint
        surf = _panel_surface(
            [hint],
            cache_key=hint_key,
            size=12,
            color=(165, 175, 190),
            bg=(0, 0, 0, 150),
            border=(50, 55, 65),
        )
        _draw_surface(MARGIN, height - surf.get_height() - MARGIN, surf, height, cache_key=hint_key)

    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)
    glEnable(GL_DEPTH_TEST)

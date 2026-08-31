"""Tests for photo mode."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nyc_world.city.world_clock import Weather, WorldClock
from nyc_world.modes.photo import PhotoMode
from nyc_world.render.camera import FreeFlyCamera


def test_photo_toggle_restores_camera():
    photo = PhotoMode()
    assert photo.toggle(px=10, py=2, pz=20, yaw=0.5, pitch=-0.2, sim_hour=8, sim_minute=30)
    assert photo.active
    assert photo.visual_hour == 8
    yaw, pitch = photo.restore_yaw_pitch()
    assert yaw == 0.5
    assert pitch == -0.2
    photo.toggle(px=10, py=2, pz=20, yaw=0.5, pitch=-0.2, sim_hour=8, sim_minute=30)
    assert not photo.active


def test_time_slider_changes_sky_color():
    photo = PhotoMode(active=True)
    photo.set_time_fraction(0.25)
    dawn_clock = photo.visual_clock(WorldClock(hour=12, minute=0))
    photo.set_time_fraction(0.75)
    dusk_clock = photo.visual_clock(WorldClock(hour=12, minute=0))
    assert dawn_clock.sky_color() != dusk_clock.sky_color()


def test_slider_bars_in_hud():
    photo = PhotoMode(active=True, visual_hour=12, visual_minute=0)
    lines = photo.hud_lines()
    assert any("●" in line for line in lines)
    assert any("Vignette" in line for line in lines)


def test_visual_clock_override():
    photo = PhotoMode(active=True, visual_hour=18, visual_minute=30, visual_weather="rain")
    sim = WorldClock(hour=8, minute=0, weather=Weather.CLEAR)
    visual = photo.visual_clock(sim)
    assert visual.hour == 18
    assert visual.minute == 30
    assert visual.weather == Weather.RAIN


def test_visual_clock_sync_mode():
    photo = PhotoMode(active=True, sync_sim_clock=True, visual_hour=18)
    sim = WorldClock(hour=8, minute=0)
    assert photo.visual_clock(sim) is sim


def test_free_fly_camera_moves():
    cam = FreeFlyCamera(x=0, y=5, z=0, yaw=0.0)
    cam.move(forward=1.0, strafe=0.0, vertical=0.0, dt=1.0)
    assert cam.z > 0


def test_screenshot_path_format(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("nyc_world.modes.photo.SCREENSHOTS_DIR", tmp_path)
    photo = PhotoMode()
    path = photo.screenshot_path()
    assert path.parent == tmp_path
    assert path.suffix == ".png"
    assert len(path.stem) >= 10


def test_capture_frame_writes_png(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("nyc_world.modes.photo.SCREENSHOTS_DIR", tmp_path)
    photo = PhotoMode()
    fake_data = b"\x00" * (4 * 4 * 3)
    with patch("OpenGL.GL.glReadPixels", return_value=fake_data):
        with patch("pygame.image.fromstring") as fromstring, patch("pygame.image.save") as save:
            surf = MagicMock()
            fromstring.return_value = surf
            path = photo.capture_frame(4, 4)
    save.assert_called_once()
    assert path.parent == tmp_path

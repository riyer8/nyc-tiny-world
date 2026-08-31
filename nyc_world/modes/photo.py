"""Photo mode — free-fly camera, visual overrides, and screenshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from nyc_world.city.world_clock import Weather, WorldClock
from nyc_world.paths import SCREENSHOTS_DIR
from nyc_world.render.camera import FreeFlyCamera


@dataclass
class PhotoMode:
    active: bool = False
    camera: FreeFlyCamera = field(default_factory=FreeFlyCamera)
    visual_hour: int | None = None
    visual_minute: int = 0
    visual_weather: str | None = None
    sync_sim_clock: bool = False
    pause_simulation: bool = True
    vignette: float = 0.35
    saved_yaw: float = 0.0
    saved_pitch: float = -0.3

    def toggle(self, *, px: float, py: float, pz: float, yaw: float, pitch: float, sim_hour: int = 12, sim_minute: int = 0) -> bool:
        if not self.active:
            self.saved_yaw = yaw
            self.saved_pitch = pitch
            self.camera.x = px
            self.camera.y = py + 4.0
            self.camera.z = pz
            self.camera.yaw = yaw
            self.camera.pitch = pitch
            if self.visual_hour is None:
                self.visual_hour = sim_hour
                self.visual_minute = sim_minute
            self.active = True
        else:
            self.active = False
        return self.active

    def restore_yaw_pitch(self) -> tuple[float, float]:
        return self.saved_yaw, self.saved_pitch

    def visual_clock(self, sim_clock: WorldClock) -> WorldClock:
        if self.sync_sim_clock or self.visual_hour is None:
            return sim_clock
        clock = WorldClock(
            hour=self.visual_hour,
            minute=self.visual_minute,
            day=sim_clock.day,
            speed=sim_clock.speed,
        )
        weather_key = self.visual_weather or sim_clock.weather.value
        try:
            clock.weather = Weather(weather_key)
        except ValueError:
            clock.weather = sim_clock.weather
        return clock

    def adjust_hour(self, delta: float) -> None:
        base = self.visual_hour if self.visual_hour is not None else 12
        total = (base * 60 + self.visual_minute + int(delta * 60)) % (24 * 60)
        self.visual_hour = total // 60
        self.visual_minute = total % 60

    @property
    def time_fraction(self) -> float:
        if self.visual_hour is None:
            return 0.5
        return (self.visual_hour * 60 + self.visual_minute) / (24 * 60)

    def set_time_fraction(self, fraction: float) -> None:
        fraction = max(0.0, min(1.0, fraction))
        total = int(fraction * 24 * 60) % (24 * 60)
        self.visual_hour = total // 60
        self.visual_minute = total % 60

    def set_fov_fraction(self, fraction: float) -> None:
        self.camera.fov = 35.0 + max(0.0, min(1.0, fraction)) * 75.0

    @property
    def fov_fraction(self) -> float:
        return (self.camera.fov - 35.0) / 75.0

    def adjust_vignette(self, delta: float) -> None:
        self.vignette = max(0.0, min(1.0, self.vignette + delta))

    def cycle_weather(self) -> str:
        order = [w.value for w in Weather]
        current = self.visual_weather or Weather.CLEAR.value
        idx = order.index(current) if current in order else 0
        self.visual_weather = order[(idx + 1) % len(order)]
        return self.visual_weather

    def adjust_fov(self, delta: float) -> float:
        self.camera.fov = max(35.0, min(110.0, self.camera.fov + delta))
        return self.camera.fov

    def hud_lines(self) -> list[str]:
        hour = self.visual_hour if self.visual_hour is not None else "sync"
        weather = self.visual_weather or "sync"
        time_bar = self._slider_bar(self.time_fraction)
        fov_bar = self._slider_bar(self.fov_fraction)
        vig_bar = self._slider_bar(self.vignette)
        return [
            "📸 PHOTO MODE",
            f"Time  {hour}:{self.visual_minute:02d}  {time_bar}",
            f"FOV   {self.camera.fov:.0f}°          {fov_bar}",
            f"Vignette {self.vignette:.0%}      {vig_bar}",
            f"Weather {weather}  (N)  ·  [/] time  ·  -/+ FOV  ·  ,/. vignette",
            f"Sim {'paused' if self.pause_simulation else 'running'} (Tab)  ·  Enter save  ·  P exit",
        ]

    @staticmethod
    def _slider_bar(fraction: float, width: int = 16) -> str:
        fraction = max(0.0, min(1.0, fraction))
        pos = int(fraction * (width - 1))
        chars = ["─"] * width
        chars[pos] = "●"
        return "[" + "".join(chars) + "]"

    def screenshot_path(self) -> Path:
        SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        return SCREENSHOTS_DIR / f"{stamp}.png"

    def capture_frame(self, width: int, height: int) -> Path:
        import pygame
        from OpenGL.GL import GL_RGB, GL_UNSIGNED_BYTE, glReadPixels

        data = glReadPixels(0, 0, width, height, GL_RGB, GL_UNSIGNED_BYTE)
        surf = pygame.image.fromstring(data, (width, height), "RGB", True)
        path = self.screenshot_path()
        pygame.image.save(surf, str(path))
        return path

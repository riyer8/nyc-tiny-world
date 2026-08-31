"""World clock, day/night cycle, and weather."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from enum import Enum


class Weather(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    FOG = "fog"


@dataclass
class WorldClock:
    hour: int = 8
    minute: int = 0
    day: int = 1
    speed: float = 2.0  # game minutes per real second
    weather: Weather = Weather.CLEAR
    _weather_timer: float = field(default=0.0, repr=False)
    _feed_weather_locked: bool = field(default=False, repr=False)
    _rng: random.Random = field(default_factory=lambda: random.Random(42), repr=False)

    def set_feed_weather(self, weather: Weather) -> None:
        self.weather = weather
        self._feed_weather_locked = True

    def clear_feed_weather(self) -> None:
        self._feed_weather_locked = False

    def advance(self, dt: float) -> None:
        prev_total = self.hour * 60 + self.minute
        total = prev_total + dt * self.speed
        if int(total // (24 * 60)) > int(prev_total // (24 * 60)):
            self.day += 1
        total %= 24 * 60
        self.hour = int(total // 60)
        self.minute = int(total % 60)

        self._weather_timer += dt
        if not self._feed_weather_locked and self._weather_timer > 120:
            self._weather_timer = 0.0
            roll = self._rng.random()
            if roll < 0.15:
                self.weather = Weather.RAIN
            elif roll < 0.35:
                self.weather = Weather.FOG
            elif roll < 0.55:
                self.weather = Weather.CLOUDY
            else:
                self.weather = Weather.CLEAR

    @property
    def time_str(self) -> str:
        suffix = "AM" if self.hour < 12 else "PM"
        h = self.hour % 12
        if h == 0:
            h = 12
        return f"{h:02d}:{self.minute:02d} {suffix}"

    @property
    def is_night(self) -> bool:
        return self.hour < 6 or self.hour >= 20

    @property
    def is_raining(self) -> bool:
        return self.weather == Weather.RAIN

    def sky_color(self) -> tuple[float, float, float]:
        t = self.hour + self.minute / 60.0
        if self.weather == Weather.RAIN:
            return (0.35, 0.38, 0.42)
        if self.weather == Weather.FOG:
            return (0.55, 0.56, 0.58)
        if self.weather == Weather.CLOUDY:
            base = 0.65
            return (base * 0.85, base * 0.88, base * 0.95)

        if 6 <= t < 8:
            p = (t - 6) / 2
            return (0.4 + 0.2 * p, 0.5 + 0.25 * p, 0.7 + 0.2 * p)
        if 8 <= t < 18:
            return (0.53, 0.73, 0.92)
        if 18 <= t < 20:
            p = (t - 18) / 2
            return (0.53 - 0.2 * p, 0.45 - 0.15 * p, 0.7 - 0.3 * p)
        return (0.08, 0.10, 0.22)

    def ambient_brightness(self) -> float:
        t = self.hour + self.minute / 60.0
        if self.is_night:
            base = 0.35
        elif 6 <= t < 8 or 18 <= t < 20:
            base = 0.65
        else:
            base = 1.0
        if self.weather == Weather.RAIN:
            base *= 0.7
        if self.weather == Weather.FOG:
            base *= 0.75
        if self.weather == Weather.CLOUDY:
            base *= 0.85
        return base

    def fog_density(self) -> float:
        if self.weather == Weather.FOG:
            return 0.04
        if self.weather == Weather.RAIN:
            return 0.015
        if self.is_night:
            return 0.008
        return 0.0

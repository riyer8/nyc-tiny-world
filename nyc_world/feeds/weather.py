"""Optional live weather fetch via Open-Meteo (no API key)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from nyc_world.feeds.parsers import parse_open_meteo

# Washington Square Park area
DEFAULT_LAT = 40.7308
DEFAULT_LON = -73.9973
OPEN_METEO_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={DEFAULT_LAT}&longitude={DEFAULT_LON}"
    "&current=weather_code&hourly=weather_code&timezone=America%2FNew_York"
)


def fetch_open_meteo(*, timeout: float = 8.0) -> dict | None:
    try:
        with urllib.request.urlopen(OPEN_METEO_URL, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


def fetch_weather_alert() -> "WeatherAlert | None":
    from nyc_world.feeds.types import WeatherAlert

    data = fetch_open_meteo()
    if not data:
        return None
    return parse_open_meteo(data)

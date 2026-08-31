"""Poll, cache, and apply NYC live feeds."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from nyc_world.city.world_clock import Weather
from nyc_world.feeds.effects import (
    SimulationModifiers,
    banner_lines,
    count_transit_affected_npcs,
    modifiers_from_feed,
)
from nyc_world.feeds.parsers import parse_feed_bundle, parse_mta_alerts
from nyc_world.feeds.types import CityFeedState
from nyc_world.feeds.weather import fetch_weather_alert
from nyc_world.paths import FEEDS_DIR

CACHE_FILE = "latest.json"
DEFAULT_POLL_INTERVAL_S = 300.0


class FeedManager:
    """Poll external feeds, cache locally, and apply effects to the city sim."""

    def __init__(
        self,
        *,
        cache_dir: Path | None = None,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        offline: bool = True,
        live_weather: bool = False,
    ) -> None:
        self.cache_dir = cache_dir or FEEDS_DIR
        self.poll_interval_s = poll_interval_s
        self.offline = offline
        self.live_weather = live_weather and not offline
        self.feed_state = CityFeedState.empty()
        self.modifiers = SimulationModifiers()
        self._last_poll = 0.0

    def poll(self, *, force: bool = False) -> CityFeedState:
        now = time.monotonic()
        if not force and now - self._last_poll < self.poll_interval_s:
            return self.feed_state

        if self.offline:
            cached = self._load_cache()
            if cached:
                self.feed_state = cached
            else:
                self.feed_state = CityFeedState.empty()
            self.modifiers = modifiers_from_feed(self.feed_state)
            self._last_poll = now
            return self.feed_state

        state = CityFeedState.empty()
        state.source = "live"

        if self.live_weather:
            alert = fetch_weather_alert()
            if alert:
                state.weather = alert

        cached = self._load_cache()
        if cached:
            if not state.weather and cached.weather:
                state.weather = cached.weather
            state.transit.extend(cached.transit)
            state.events.extend(cached.events)

        state.last_updated = datetime.now(timezone.utc).isoformat()
        self.feed_state = state
        self.modifiers = modifiers_from_feed(state)
        self._write_cache(state)
        self._last_poll = now
        return state

    def load_from_dict(self, data: dict) -> CityFeedState:
        self.feed_state = parse_feed_bundle(data)
        self.modifiers = modifiers_from_feed(self.feed_state)
        self._write_cache(self.feed_state)
        return self.feed_state

    def load_from_file(self, path: Path) -> CityFeedState:
        data = json.loads(path.read_text())
        return self.load_from_dict(data)

    def apply_to_sim(self, city) -> SimulationModifiers:
        """Apply current feed state to a CitySimulation."""
        mods = modifiers_from_feed(self.feed_state)
        city.feed_modifiers = mods

        if mods.weather_override:
            try:
                city.clock.set_feed_weather(Weather(mods.weather_override))
            except ValueError:
                city.clock.clear_feed_weather()
        else:
            city.clock.clear_feed_weather()

        subway_positions = getattr(city, "subway_positions", [])
        npc_positions = {npc.name: (npc.x, npc.z) for npc in getattr(city, "npcs", [])}
        mods.transit_affected_npcs = count_transit_affected_npcs(
            npc_positions, subway_positions, mods
        )
        city.feed_modifiers = mods
        self.modifiers = mods
        return mods

    def hud_banner(self) -> list[str]:
        return banner_lines(self.feed_state)

    def _cache_path(self) -> Path:
        return self.cache_dir / CACHE_FILE

    def _load_cache(self) -> CityFeedState | None:
        path = self._cache_path()
        if not path.exists():
            return None
        try:
            return parse_feed_bundle(json.loads(path.read_text()))
        except (json.JSONDecodeError, OSError, KeyError):
            return None

    def _write_cache(self, state: CityFeedState) -> None:
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path().write_text(json.dumps(state.to_dict(), indent=2))

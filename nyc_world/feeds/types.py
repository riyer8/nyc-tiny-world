"""Serializable feed data types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class WeatherAlert:
    condition: str
    summary: str
    expected_hour: int | None = None

    def to_dict(self) -> dict:
        return {
            "condition": self.condition,
            "summary": self.summary,
            "expected_hour": self.expected_hour,
        }

    @classmethod
    def from_dict(cls, data: dict) -> WeatherAlert:
        return cls(
            condition=data.get("condition", "clear"),
            summary=data.get("summary", ""),
            expected_hour=data.get("expected_hour"),
        )


@dataclass
class TransitAlert:
    line: str
    delay_minutes: int
    summary: str

    def to_dict(self) -> dict:
        return {
            "line": self.line,
            "delay_minutes": self.delay_minutes,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: dict) -> TransitAlert:
        return cls(
            line=data.get("line", ""),
            delay_minutes=int(data.get("delay_minutes", 0)),
            summary=data.get("summary", ""),
        )


@dataclass
class CityEvent:
    title: str
    location: str
    start_hour: int | None = None

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "location": self.location,
            "start_hour": self.start_hour,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CityEvent:
        return cls(
            title=data.get("title", ""),
            location=data.get("location", ""),
            start_hour=data.get("start_hour"),
        )


@dataclass
class CityFeedState:
    weather: WeatherAlert | None = None
    transit: list[TransitAlert] = field(default_factory=list)
    events: list[CityEvent] = field(default_factory=list)
    last_updated: str = ""
    source: str = "offline"

    def to_dict(self) -> dict:
        return {
            "weather": self.weather.to_dict() if self.weather else None,
            "transit": [t.to_dict() for t in self.transit],
            "events": [e.to_dict() for e in self.events],
            "last_updated": self.last_updated,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> CityFeedState:
        weather = data.get("weather")
        return cls(
            weather=WeatherAlert.from_dict(weather) if weather else None,
            transit=[TransitAlert.from_dict(t) for t in data.get("transit", [])],
            events=[CityEvent.from_dict(e) for e in data.get("events", [])],
            last_updated=data.get("last_updated", ""),
            source=data.get("source", "offline"),
        )

    @classmethod
    def empty(cls) -> CityFeedState:
        return cls(last_updated=datetime.now(timezone.utc).isoformat(), source="offline")

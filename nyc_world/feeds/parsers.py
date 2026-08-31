"""Parse feed JSON from cache files and external APIs."""

from __future__ import annotations

from datetime import datetime, timezone

from nyc_world.feeds.types import CityEvent, CityFeedState, TransitAlert, WeatherAlert


def parse_feed_bundle(data: dict) -> CityFeedState:
    """Parse a combined feed cache file."""
    weather = data.get("weather")
    transit = data.get("transit", data.get("transit_alerts", []))
    events = data.get("events", [])
    return CityFeedState(
        weather=WeatherAlert.from_dict(weather) if weather else None,
        transit=[TransitAlert.from_dict(t) for t in transit],
        events=[CityEvent.from_dict(e) for e in events],
        last_updated=data.get("last_updated", datetime.now(timezone.utc).isoformat()),
        source=data.get("source", "cache"),
    )


def parse_open_meteo(data: dict) -> WeatherAlert | None:
    """Map Open-Meteo response to a weather alert."""
    current = data.get("current", {})
    code = current.get("weather_code")
    if code is None:
        hourly = data.get("hourly", {})
        codes = hourly.get("weather_code", [])
        times = hourly.get("time", [])
        if not codes:
            return None
        code = codes[0]
        expected_hour = None
        if times:
            try:
                expected_hour = int(times[0].split("T")[1].split(":")[0])
            except (IndexError, ValueError):
                expected_hour = None
    else:
        expected_hour = None

    condition = _wmo_to_condition(int(code))
    summary = _summary_for_condition(condition, expected_hour)
    return WeatherAlert(condition=condition, summary=summary, expected_hour=expected_hour)


def parse_mta_alerts(data: dict) -> list[TransitAlert]:
    """Parse MTA-style delay JSON."""
    alerts: list[TransitAlert] = []
    for item in data.get("alerts", data.get("entity", [])):
        if "alert" in item:
            item = item["alert"]
        line = item.get("line") or item.get("route_id", "")
        delay = int(item.get("delay_minutes", item.get("delay", 0)))
        summary = item.get("summary") or item.get("header_text", "")
        if line or summary:
            alerts.append(TransitAlert(line=line, delay_minutes=delay, summary=summary))
    return alerts


def _wmo_to_condition(code: int) -> str:
    if code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99):
        return "rain"
    if code in (45, 48):
        return "fog"
    if code in (1, 2, 3):
        return "cloudy"
    return "clear"


def _summary_for_condition(condition: str, hour: int | None) -> str:
    if condition == "rain":
        if hour is not None:
            suffix = "AM" if hour < 12 else "PM"
            h = hour % 12 or 12
            return f"Rain expected at {h} {suffix} (live forecast)"
        return "Rain in the forecast (live)"
    if condition == "fog":
        return "Fog advisory (live forecast)"
    if condition == "cloudy":
        return "Cloudy skies (live forecast)"
    return "Clear skies (live forecast)"
